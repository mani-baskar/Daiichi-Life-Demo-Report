#!/usr/bin/env python3
"""Train a leakage-safe lead conversion model and score current open leads."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


CATEGORICAL_FEATURES = [
    "LeadSource",
    "DistributionChannel",
    "Region",
    "IncomeBandSGD",
    "ExistingCustomerFlag",
    "ProductInterest",
    "AgentKey",
]

NUMERIC_FEATURES = [
    "EstimatedAnnualPremiumSGD",
    "ContactAttempts",
    "FirstResponseHours",
    "FollowUpCount",
    "DigitalEngagementScore",
    "NeedsAssessmentScore",
    "AppointmentCompletedFlag",
    "QuoteProvidedFlag",
    "DaysSinceLeadCreated",
]

LEAKAGE_AND_GOVERNANCE_EXCLUSIONS = [
    "ConvertedFlag",
    "ConversionDate",
    "LostReason",
    "LeadStage",
    "ConversionProbability",
    "PredictedConvertedFlag",
    "PropensityBand",
    "ModelVersion",
    "ScoredAt",
    "Gender",
    "MaritalStatus",
    "AgeBand",
    "PlanningArea",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=20260925)
    parser.add_argument("--max-historical-rows", type=int, default=250000)
    return parser.parse_args()


def make_preprocessor() -> ColumnTransformer:
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("categorical", categorical, CATEGORICAL_FEATURES),
            ("numeric", numeric, NUMERIC_FEATURES),
        ]
    )


def evaluate(model: Pipeline, x_test: pd.DataFrame, y_test: pd.Series) -> dict[str, Any]:
    probability = model.predict_proba(x_test)[:, 1]
    predicted = (probability >= 0.5).astype(int)
    matrix = confusion_matrix(y_test, predicted, labels=[0, 1])
    return {
        "roc_auc": float(roc_auc_score(y_test, probability)),
        "precision": float(precision_score(y_test, predicted, zero_division=0)),
        "recall": float(recall_score(y_test, predicted, zero_division=0)),
        "f1": float(f1_score(y_test, predicted, zero_division=0)),
        "confusion_matrix": matrix.tolist(),
    }


def propensity_band(probability: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [probability.ge(0.65), probability.ge(0.35)],
            ["High", "Medium"],
            default="Low",
        ),
        index=probability.index,
    )


def main() -> int:
    args = parse_args()
    root = (args.project_root or Path(__file__).resolve().parents[1]).resolve()
    curated = root / "data" / "curated"
    validation = root / "validation"
    validation.mkdir(parents=True, exist_ok=True)

    leads = pd.read_csv(curated / "LeadConversion.csv", parse_dates=["LeadCreatedDate"])
    agents = pd.read_csv(curated / "DimAgent.csv")
    historical = leads.loc[
        leads["ConvertedFlag"].notna() & leads["LeadStage"].isin(["Won", "Lost"])
    ].copy()
    historical["ConvertedFlag"] = historical["ConvertedFlag"].astype(int)
    historical = historical.sort_values(["LeadCreatedDate", "LeadID"]).reset_index(drop=True)
    if len(historical) > args.max_historical_rows:
        historical = historical.tail(args.max_historical_rows).reset_index(drop=True)
    if len(historical) < 200 or historical["ConvertedFlag"].nunique() != 2:
        raise RuntimeError("Not enough completed leads from both classes for the ML demo")

    split_index = int(len(historical) * 0.75)
    train = historical.iloc[:split_index]
    test = historical.iloc[split_index:]
    if train["ConvertedFlag"].nunique() != 2 or test["ConvertedFlag"].nunique() != 2:
        raise RuntimeError("Time split must contain both target classes in train and test")

    features = CATEGORICAL_FEATURES + NUMERIC_FEATURES
    x_train, y_train = train[features], train["ConvertedFlag"]
    x_test, y_test = test[features], test["ConvertedFlag"]

    candidates: dict[str, Pipeline] = {
        "logistic_regression": Pipeline(
            steps=[
                ("preprocessor", make_preprocessor()),
                ("classifier", LogisticRegression(max_iter=1200, class_weight="balanced", random_state=args.seed)),
            ]
        ),
        "random_forest": Pipeline(
            steps=[
                ("preprocessor", make_preprocessor()),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=260,
                        max_depth=9,
                        min_samples_leaf=10,
                        class_weight="balanced_subsample",
                        random_state=args.seed,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }

    metrics: dict[str, dict[str, Any]] = {}
    for name, candidate in candidates.items():
        candidate.fit(x_train, y_train)
        metrics[name] = evaluate(candidate, x_test, y_test)

    best_name = max(metrics, key=lambda name: metrics[name]["roc_auc"])
    best_auc = metrics[best_name]["roc_auc"]
    if best_auc < 0.62:
        raise RuntimeError(f"Best ROC-AUC {best_auc:.3f} does not meaningfully beat random baseline")
    if best_auc > 0.95:
        raise RuntimeError(f"Best ROC-AUC {best_auc:.3f} is unrealistically high for this demo")

    best_model = candidates[best_name]
    best_model.fit(historical[features], historical["ConvertedFlag"])
    open_leads = leads.loc[~leads["LeadStage"].isin(["Won", "Lost"])].copy()
    if open_leads.empty:
        raise RuntimeError("No open leads available for scoring")
    probability = pd.Series(best_model.predict_proba(open_leads[features])[:, 1], index=open_leads.index)
    open_leads["ConversionProbability"] = probability.round(6)
    open_leads["PredictedConvertedFlag"] = probability.ge(0.5).astype(int)
    open_leads["PropensityBand"] = propensity_band(probability)
    model_version = f"{best_name}-synthetic-v1"
    open_leads["ModelVersion"] = model_version
    scored_at = pd.Timestamp(leads["LeadCreatedDate"].max()).normalize() + pd.Timedelta(hours=23, minutes=59)
    open_leads["ScoredAt"] = scored_at
    open_leads = open_leads.merge(agents[["AgentKey", "AgentName"]], on="AgentKey", how="left", validate="many_to_one")

    output_columns = [
        "LeadID", "ProductKey", "AgentKey", "AgentName", "ProductInterest",
        "DistributionChannel", "Region", "PlanningArea", "EstimatedAnnualPremiumSGD",
        "DaysSinceLeadCreated", "LeadStage", "ConversionProbability",
        "PredictedConvertedFlag", "PropensityBand", "ModelVersion", "ScoredAt",
    ]
    scored = open_leads[output_columns].sort_values("ConversionProbability", ascending=False)
    scored.to_csv(curated / "LeadPropensity.csv", index=False, encoding="utf-8", date_format="%Y-%m-%d %H:%M:%S")
    try:
        scored.to_parquet(curated / "LeadPropensity.parquet", index=False)
        parquet_written = True
    except (ImportError, ModuleNotFoundError):
        parquet_written = False

    metrics_output = {
        "dataset": "synthetic",
        "split_strategy": "chronological 75/25",
        "train_rows": len(train),
        "test_rows": len(test),
        "open_leads_scored": len(scored),
        "historical_conversion_rate": float(historical["ConvertedFlag"].mean()),
        "features": features,
        "excluded_fields": LEAKAGE_AND_GOVERNANCE_EXCLUSIONS,
        "candidate_metrics": metrics,
        "selected_model": best_name,
        "model_version": model_version,
        "random_baseline_auc": 0.5,
        "parquet_written": parquet_written,
    }
    (validation / "ml_metrics.json").write_text(json.dumps(metrics_output, indent=2), encoding="utf-8")

    report = [
        "# Lead Conversion ML Report",
        "",
        "> This model uses synthetic demo data only. Scores are prioritization aids, not automated eligibility or underwriting decisions.",
        "",
        "## Split and governance",
        "",
        f"- Chronological train/test split: {len(train):,} / {len(test):,} completed leads",
        f"- Historical conversion rate: {historical['ConvertedFlag'].mean():.2%}",
        f"- Open leads scored: {len(scored):,}",
        "- Gender, marital status, age band and exact location are excluded.",
        "- Outcome, final-stage and prior model-output fields are excluded.",
        "",
        "## Candidate metrics",
        "",
        "| Model | ROC-AUC | Precision | Recall | F1 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, values in metrics.items():
        report.append(f"| {name} | {values['roc_auc']:.3f} | {values['precision']:.3f} | {values['recall']:.3f} | {values['f1']:.3f} |")
    report.extend([
        "",
        f"Selected model: `{best_name}` (`{model_version}`)",
        f"Best ROC-AUC: `{best_auc:.3f}` versus random baseline `0.500`.",
        "",
        "The Fabric notebook version logs the experiment to MLflow and writes the equivalent scored output to `gold_lead_propensity`.",
        "",
    ])
    (validation / "ml_model_report.md").write_text("\n".join(report), encoding="utf-8")

    print(f"Selected {best_name}; test ROC-AUC={best_auc:.3f}; scored {len(scored):,} open leads.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
