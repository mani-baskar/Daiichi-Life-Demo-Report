# Lead Conversion ML Report

> This model uses synthetic demo data only. Scores are prioritization aids, not automated eligibility or underwriting decisions.

## Split and governance

- Chronological train/test split: 3,991 / 1,331 completed leads
- Historical conversion rate: 39.93%
- Open leads scored: 678
- Gender, marital status, age band and exact location are excluded.
- Outcome, final-stage and prior model-output fields are excluded.

## Candidate metrics

| Model | ROC-AUC | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: |
| logistic_regression | 0.772 | 0.619 | 0.701 | 0.657 |
| random_forest | 0.770 | 0.638 | 0.681 | 0.659 |

Selected model: `logistic_regression` (`logistic_regression-synthetic-v1`)
Best ROC-AUC: `0.772` versus random baseline `0.500`.

The Fabric notebook version logs the experiment to MLflow and writes the equivalent scored output to `gold_lead_propensity`.
