# Fabric notebook source
# Attach this notebook to the Lakehouse that contains silver_lead_conversion
# and silver_dim_agent. The local src/run_ml_demo.py script is the executable
# smoke-test equivalent used by this repository.

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 20260925
CATEGORICAL = [
    "LeadSource", "DistributionChannel", "Region", "IncomeBandSGD",
    "ExistingCustomerFlag", "ProductInterest", "AgentKey",
]
NUMERIC = [
    "EstimatedAnnualPremiumSGD", "ContactAttempts", "FirstResponseHours",
    "FollowUpCount", "DigitalEngagementScore", "NeedsAssessmentScore",
    "AppointmentCompletedFlag", "QuoteProvidedFlag", "DaysSinceLeadCreated",
]
FEATURES = CATEGORICAL + NUMERIC

# Leakage and governance exclusions are intentional:
# ConversionDate, LostReason, LeadStage, prediction outputs, Gender,
# MaritalStatus, AgeBand and exact location are not model features.
leads = spark.table("silver_lead_conversion").toPandas()
agents = spark.table("silver_dim_agent").select("AgentKey", "AgentName").toPandas()
leads["LeadCreatedDate"] = pd.to_datetime(leads["LeadCreatedDate"])

historical = leads.loc[
    leads["ConvertedFlag"].notna() & leads["LeadStage"].isin(["Won", "Lost"])
].sort_values(["LeadCreatedDate", "LeadID"]).copy()
historical["ConvertedFlag"] = historical["ConvertedFlag"].astype(int)
split = int(len(historical) * 0.75)
train, test = historical.iloc[:split], historical.iloc[split:]


def preprocessor():
    return ColumnTransformer(
        [
            ("categorical", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAL),
            ("numeric", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), NUMERIC),
        ]
    )


candidates = {
    "logistic_regression": Pipeline([("preprocessor", preprocessor()), ("classifier", LogisticRegression(max_iter=1200, class_weight="balanced", random_state=SEED))]),
    "random_forest": Pipeline([("preprocessor", preprocessor()), ("classifier", RandomForestClassifier(n_estimators=260, max_depth=9, min_samples_leaf=10, class_weight="balanced_subsample", random_state=SEED, n_jobs=-1))]),
}

mlflow.set_experiment("insurance_lead_conversion")
results = {}
for name, model in candidates.items():
    with mlflow.start_run(run_name=name):
        model.fit(train[FEATURES], train["ConvertedFlag"])
        probability = model.predict_proba(test[FEATURES])[:, 1]
        predicted = (probability >= 0.5).astype(int)
        results[name] = {
            "roc_auc": roc_auc_score(test["ConvertedFlag"], probability),
            "precision": precision_score(test["ConvertedFlag"], predicted, zero_division=0),
            "recall": recall_score(test["ConvertedFlag"], predicted, zero_division=0),
            "f1": f1_score(test["ConvertedFlag"], predicted, zero_division=0),
        }
        mlflow.log_metrics(results[name])
        mlflow.log_params({"time_split": "75/25", "feature_count": len(FEATURES), "seed": SEED})
        mlflow.sklearn.log_model(model, artifact_path="model")

best_name = max(results, key=lambda name: results[name]["roc_auc"])
best_model = candidates[best_name]
best_model.fit(historical[FEATURES], historical["ConvertedFlag"])

open_leads = leads.loc[~leads["LeadStage"].isin(["Won", "Lost"])].copy()
probability = pd.Series(best_model.predict_proba(open_leads[FEATURES])[:, 1], index=open_leads.index)
open_leads["ConversionProbability"] = probability.round(6)
open_leads["PredictedConvertedFlag"] = probability.ge(0.5).astype(int)
open_leads["PropensityBand"] = np.select([probability.ge(0.65), probability.ge(0.35)], ["High", "Medium"], default="Low")
open_leads["ModelVersion"] = f"{best_name}-fabric-v1"
open_leads["ScoredAt"] = pd.Timestamp.utcnow()
open_leads = open_leads.merge(agents, on="AgentKey", how="left", validate="many_to_one")

output_columns = [
    "LeadID", "ProductKey", "AgentKey", "AgentName", "ProductInterest",
    "DistributionChannel", "Region", "PlanningArea", "EstimatedAnnualPremiumSGD",
    "DaysSinceLeadCreated", "LeadStage", "ConversionProbability",
    "PredictedConvertedFlag", "PropensityBand", "ModelVersion", "ScoredAt",
]
spark.createDataFrame(open_leads[output_columns]).write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("gold_lead_propensity")

print(pd.DataFrame(results).T.sort_values("roc_auc", ascending=False))
print(f"Selected {best_name}; scored {len(open_leads):,} open leads")
