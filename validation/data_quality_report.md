# Data Quality Report

Generated: 2026-09-25T23:03:20
Scale: `small`
Random seed: `20260925`
Business date range: `2023-01-01` to `2026-09-25`
DimDate range: `2023-01-01` to `2027-09-26` (includes renewal-key buffer)

> All records are synthetic. They do not represent Daiichi Life customers or business performance.

## Outcome

**PASS** - 15 of 15 mandatory checks passed.

## Curated row counts

| Table | Rows |
| --- | ---: |
| DimDate | 1,730 |
| DimCustomer | 750 |
| DimProduct | 12 |
| DimAgent | 25 |
| FactPolicy | 2,500 |
| LeadConversion | 6,000 |

## ML target

Historical completed leads: 5,322
Converted share: 39.93%
Open leads keep the outcome fields blank and are intended for scoring.

## Validation checks

| Check | Observed | Expected | Status |
| --- | ---: | --- | --- |
| Primary key duplicates | 0 | 0 | PASS |
| Orphan foreign keys | 0 | 0 | PASS |
| Invalid date sequence | 0 | 0 | PASS |
| Invalid age/product eligibility | 0 | 0 | PASS |
| Non-positive premium or sum assured | 0 | 0 | PASS |
| Invalid claim amount | 0 | 0 | PASS |
| Geography mapping | 0 | 0 invalid pairs | PASS |
| Policy status logic | 0 | 0 | PASS |
| ML target balance | 39.93% | 15%-65% converted | PASS |
| Leakage fields excluded | 0 | 0 leakage features | PASS |
| Every month represented | 0 | 0 missing months | PASS |
| Product family and channel coverage | 0 | All required categories | PASS |
| Map fields available | 0 | 0 missing/out-of-range | PASS |
| Currency fields numeric | 0 | 0 non-numeric columns | PASS |
| Incremental-load timestamps | 0 | 0 missing | PASS |

## Raw-layer quality simulation

Controlled issues exist only in non-key raw fields. The curated tables retain their clean values.

| Raw field issue | Rows |
| --- | ---: |
| DimAgent.AgentName.space | 1 |
| DimAgent.BranchName.missing | 1 |
| DimCustomer.OccupationCategory.missing | 8 |
| DimCustomer.PlanningArea.space | 8 |
| DimProduct.TypicalPremiumBand.space | 1 |
| FactPolicy.AcquisitionChannel.space | 25 |
| FactPolicy.PaymentFrequency.missing | 25 |
| LeadConversion.FirstResponseHours.missing | 60 |
| LeadConversion.LeadSource.space | 60 |

## Output formats

CSV files: 12
Parquet files: 12
