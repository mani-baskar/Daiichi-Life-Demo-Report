# Life Insurance Growth & Customer Analytics Demo

Synthetic life-insurance data and a lead-conversion ML demonstration for an Azure, Microsoft Fabric and Power BI interview scenario.

> This project contains no real PII or Daiichi Life business data. The products, customers, agents, policies and performance values are fictional. Do not present its metrics as actual Daiichi Life results.

## What is included

```text
config/demo_config.json                  Scale, seed and date settings
src/generate_insurance_demo_data.py      Raw/curated data generator and validation
src/run_ml_demo.py                       Leakage-safe local model smoke test
notebooks/NB_Lead_Conversion_Model.py    Fabric notebook source with MLflow flow
data/raw/                                Source-like data with controlled quality issues
data/curated/                            Clean Power BI/Fabric-ready tables
validation/                              Data-quality and model reports
docs/data_dictionary.md                  Column definitions
docs/relationship_model.md               Star-schema relationship guidance
```

The six source tables are `DimDate`, `DimCustomer`, `DimProduct`, `DimAgent`, `FactPolicy` and `LeadConversion`. The ML step creates the downstream `LeadPropensity` output for current open leads.

## Setup

Python 3.11+ is recommended.

```powershell
python -m pip install -r requirements.txt
```

`pyarrow` enables Parquet output. If it is unavailable, the generator still writes CSV files and records the Parquet skip in the quality report.

## Generate the dataset

```powershell
python src/generate_insurance_demo_data.py --scale small
python src/generate_insurance_demo_data.py --scale medium
python src/generate_insurance_demo_data.py --scale large
```

Useful overrides:

```powershell
python src/generate_insurance_demo_data.py --scale small --seed 42 --end-date 2026-12-31
python src/generate_insurance_demo_data.py --scale small --no-parquet
```

The generator exits with a non-zero status when a mandatory validation fails. `DimDate` extends 366 days beyond the configured business end date so every future first-renewal key remains valid; business events remain within the configured demo period.

Configured scale volumes:

| Scale | Customers | Agents | Policies | Leads |
| --- | ---: | ---: | ---: | ---: |
| Small | 750 | 25 | 2,500 | 6,000 |
| Medium | 15,000 | 250 | 75,000 | 180,000 |
| Large | 120,000 | 1,500 | 750,000 | 1,800,000 |

Edit [demo_config.json](config/demo_config.json) to change these counts.

## Run the ML smoke test

Generate data first, then run:

```powershell
python src/run_ml_demo.py
# Optional cap for a larger generated dataset:
python src/run_ml_demo.py --max-historical-rows 250000
```

The script:

1. Uses only completed historical `Won`/`Lost` leads for training.
2. Applies a chronological 75/25 train/test split.
3. Excludes outcomes, final stage, prior scores and sensitive/governance fields.
4. Compares logistic regression with random forest.
5. Rejects a model that does not meaningfully beat a random baseline or is unrealistically near-perfect.
6. Scores current open leads into `data/curated/LeadPropensity.csv` and Parquet when available.

For Fabric, import [NB_Lead_Conversion_Model.py](notebooks/NB_Lead_Conversion_Model.py) into a notebook attached to the Lakehouse. It reads `silver_lead_conversion`, logs candidate metrics in MLflow and writes `gold_lead_propensity` as a Delta table.

## Data layers

- `raw`: identical keys and row counts, with a controlled 1% of non-key values made missing or padded with whitespace to demonstrate Silver cleaning.
- `curated`: typed, clean data that passes referential, date, product-age, policy-status, geography and numeric checks.
- `LeadPropensity`: downstream ML output for open-lead prioritization; it is not a seventh operational source table.

CSV files use UTF-8. The fixed default seed makes repeated runs deterministic.

## Suggested platform flow

```text
Azure SQL -> Azure Data Factory -> ADLS Gen2 raw
         -> OneLake Shortcut -> Fabric Lakehouse Bronze/Silver/Gold
         -> Fabric ML + MLflow -> gold_lead_propensity
         -> Direct Lake semantic model -> Power BI
```

See the numbered implementation guides in `docs/` for the Azure, Fabric and Power BI steps that follow this dataset work.
