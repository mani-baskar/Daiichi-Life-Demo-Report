# Data Dictionary

All data is synthetic. Currency columns are Singapore dollars (SGD). Flags use `1` for true and `0` for false unless an open lead intentionally has a blank outcome.

## DimDate

Grain: one row per calendar date. The configured business period is extended by 366 days to cover future renewal keys.

| Column | Type | Description |
| --- | --- | --- |
| DateKey | Integer | Surrogate date key in `YYYYMMDD` form. |
| Date | Date | Calendar date. |
| Year | Integer | Calendar year. |
| Quarter | Text | Quarter label `Q1`-`Q4`. |
| QuarterNumber | Integer | Quarter number 1-4. |
| MonthNumber | Integer | Month number 1-12. |
| MonthName | Text | Full English month name. |
| YearMonth | Text | Sortable `YYYY-MM` label. |
| WeekOfYear | Integer | ISO week number. |
| DayOfWeek | Integer | Monday=1 through Sunday=7. |
| DayName | Text | Full English day name. |
| IsWeekend | Integer flag | Saturday or Sunday. |
| IsMonthEnd | Integer flag | Last day of a month. |
| IsQuarterEnd | Integer flag | Last day of a calendar quarter. |
| IsYearEnd | Integer flag | Last day of a calendar year. |

## DimCustomer

Grain: one row per synthetic customer. No real names, addresses or exact residential coordinates are stored.

| Column | Type | Description |
| --- | --- | --- |
| CustomerKey | Integer | Surrogate primary key. |
| CustomerID | Text | Synthetic business identifier. |
| Age | Integer | Age at the configured demo end date. |
| AgeBand | Text | `18-29`, `30-39`, `40-49`, `50-59` or `60+`. |
| Gender | Text | Reporting-only synthetic attribute; excluded from modeling. |
| OccupationCategory | Text | Broad synthetic occupation category. |
| IncomeBandSGD | Text | Annual income band, not exact income. |
| MaritalStatus | Text | Reporting-only synthetic attribute; excluded from modeling. |
| ExistingCustomerFlag | Integer flag | Customer already had a relationship at acquisition. |
| CustomerSegment | Text | `Emerging`, `Mass`, `Affluent` or `High Value`. |
| Region | Text | Singapore reporting region. |
| PlanningArea | Text | Aggregated planning area. |
| PostalSector | Text | Synthetic sector-level geography. |
| PlanningAreaLatitude | Decimal | Planning-area centroid latitude. |
| PlanningAreaLongitude | Decimal | Planning-area centroid longitude. |
| ConsentForMarketingFlag | Integer flag | Synthetic marketing-consent status. |
| CustomerSinceDate | Date | Synthetic relationship start date. |

## DimProduct

Grain: one row per fictional insurance product. Product names do not copy Daiichi Life products.

| Column | Type | Description |
| --- | --- | --- |
| ProductKey | Integer | Surrogate primary key. |
| ProductCode | Text | Synthetic product code. |
| ProductName | Text | Fictional product name. |
| ProductFamily | Text | Term, whole life, savings, investment-linked, critical illness or retirement/annuity. |
| CoverageType | Text | High-level benefit coverage. |
| RiskTier | Text | `Low`, `Standard` or `Elevated`. |
| MinEntryAge | Integer | Minimum eligible entry age. |
| MaxEntryAge | Integer | Maximum eligible entry age. |
| TypicalPremiumBand | Text | Human-readable annual premium range. |
| TypicalSumAssuredBand | Text | Human-readable sum-assured range. |
| InvestmentLinkedFlag | Integer flag | Investment-linked product indicator. |
| CriticalIllnessFlag | Integer flag | Critical-illness coverage indicator. |
| ProductActiveFlag | Integer flag | Product available in this demo. |
| ProductLaunchDate | Date | Fictional launch date. |

## DimAgent

Grain: one row per synthetic advisor, digital team or distribution entity.

| Column | Type | Description |
| --- | --- | --- |
| AgentKey | Integer | Surrogate primary key. |
| AgentID | Text | Synthetic business identifier. |
| AgentName | Text | Synthetic person/team name. |
| DistributionChannel | Text | Agency, Bancassurance, Digital, Broker / IFA or Direct. |
| BranchName | Text | Fictional advisory centre or virtual hub. |
| Region | Text | Branch reporting region. |
| PlanningArea | Text | Branch planning area. |
| BranchLatitude | Decimal | Branch planning-area centroid latitude. |
| BranchLongitude | Decimal | Branch planning-area centroid longitude. |
| AgentJoinDate | Date | Synthetic join date. |
| AgentTenureMonths | Integer | Tenure as of the demo end date. |
| AgentGrade | Text | `Associate`, `Senior` or `Premier`. |
| MonthlyTargetSGD | Decimal | Synthetic monthly premium target. |
| ActiveFlag | Integer flag | Active advisor/entity indicator. |

## FactPolicy

Grain: one row per synthetic issued or historical policy.

| Column | Type | Description |
| --- | --- | --- |
| PolicyKey | Integer | Surrogate primary key. |
| PolicyID | Text | Unique synthetic policy identifier. |
| CustomerKey | Integer | Foreign key to `DimCustomer`. |
| ProductKey | Integer | Foreign key to `DimProduct`. |
| AgentKey | Integer | Foreign key to `DimAgent`. |
| ApplicationDateKey | Integer | Active foreign key to `DimDate`. |
| IssueDateKey | Integer | Inactive role-playing foreign key to `DimDate`. |
| RenewalDateKey | Integer | Inactive role-playing foreign key to `DimDate`. |
| ApplicationDate | Date | Application received date. |
| IssueDate | Date | Policy issue date. |
| RenewalDate | Date | First renewal date. |
| PolicyStatus | Text | Active, Lapsed, Matured, Claimed or Cancelled. |
| PaymentFrequency | Text | Monthly, Quarterly, Half-yearly or Annual. |
| UnderwritingDecision | Text | Approved or Approved with Loading. |
| UnderwritingRiskBand | Text | Low, Standard or Elevated synthetic risk band. |
| DaysToIssue | Integer | Calendar days from application to issue. |
| AnnualPremiumSGD | Decimal | Annualized premium. |
| MonthlyEquivalentPremiumSGD | Decimal | Annual premium divided by 12. |
| SumAssuredSGD | Decimal | Contracted synthetic sum assured. |
| RenewalPremiumDueSGD | Decimal | First-renewal premium due within the business period; otherwise zero. |
| RenewalPremiumPaidSGD | Decimal | Paid first-renewal amount. |
| RenewalPaidFlag | Integer flag | Renewal payment received. |
| LapseFlag | Integer flag | Policy status is Lapsed. |
| ClaimCount | Integer | Synthetic claim count. |
| ClaimPaidAmountSGD | Decimal | Paid claim amount, capped below sum assured. |
| ClaimStatus | Text | `None` or `Paid` in the generated source. |
| ClaimDate | Date | Synthetic claim date; blank when no claim exists. |
| PolicyTermYears | Integer | Contract term used for maturity logic. |
| AcquisitionChannel | Text | Distribution channel at acquisition. |
| LastModifiedDateTime | Timestamp | Watermark column for incremental ingestion. |

## LeadConversion

Grain: one row per synthetic sales lead. Completed leads have `Won`/`Lost` stage and a target. Open leads have a blank target and are scored downstream.

| Column | Type | Description |
| --- | --- | --- |
| LeadID | Text | Unique synthetic lead identifier. |
| LeadCreatedDate | Date | Lead creation date. |
| LeadCreatedDateKey | Integer | Foreign key to `DimDate`. |
| ProductKey | Integer | Foreign key to `DimProduct`. |
| AgentKey | Integer | Foreign key to `DimAgent`. |
| LeadSource | Text | Website, Referral, Branch, Bancassurance, Campaign, Agent Prospecting or Existing Customer Cross-sell. |
| DistributionChannel | Text | Assigned distribution channel. |
| Region | Text | Assigned branch/team region. |
| PlanningArea | Text | Assigned branch/team planning area; excluded from modeling. |
| AgeBand | Text | Reporting field; excluded from the default model pending fairness review. |
| IncomeBandSGD | Text | Annual income band. |
| ExistingCustomerFlag | Integer flag | Existing relationship indicator. |
| ProductInterest | Text | Fictional product of interest. |
| EstimatedAnnualPremiumSGD | Decimal | Estimated annual premium. |
| ContactAttempts | Integer | Contact attempts to date. |
| FirstResponseHours | Decimal | Hours to first response. |
| FollowUpCount | Integer | Follow-up count. |
| DigitalEngagementScore | Integer | Synthetic 0-100 engagement score. |
| NeedsAssessmentScore | Integer | Synthetic 0-100 needs-assessment score. |
| AppointmentCompletedFlag | Integer flag | Appointment completed. |
| QuoteProvidedFlag | Integer flag | Quote provided. |
| DaysSinceLeadCreated | Integer | Age of lead at the demo end date. |
| LeadStage | Text | Open stage or final `Won`/`Lost`; excluded from model features. |
| ConvertedFlag | Nullable integer flag | Historical training target; blank for open leads. |
| ConversionDate | Nullable date | Outcome field; excluded from modeling. |
| LostReason | Nullable text | Outcome field; excluded from modeling. |
| ConversionProbability | Nullable decimal | Reserved model output; blank in source generation. |
| PredictedConvertedFlag | Nullable integer flag | Reserved model output; blank in source generation. |
| PropensityBand | Nullable text | Reserved High/Medium/Low model output. |
| ModelVersion | Nullable text | Reserved model-version identifier. |
| ScoredAt | Nullable timestamp | Reserved score timestamp. |
| LastModifiedDateTime | Timestamp | Watermark column for incremental ingestion. |

## LeadPropensity

Grain: one row per current open lead. Created by `src/run_ml_demo.py` locally or as `gold_lead_propensity` by the Fabric notebook.

| Column | Type | Description |
| --- | --- | --- |
| LeadID | Text | Open lead identifier. |
| ProductKey | Integer | Product relationship key. |
| AgentKey | Integer | Agent relationship key. |
| AgentName | Text | Assigned synthetic agent/team name. |
| ProductInterest | Text | Product of interest. |
| DistributionChannel | Text | Assigned channel. |
| Region | Text | Assigned region. |
| PlanningArea | Text | Reporting geography, not a model feature. |
| EstimatedAnnualPremiumSGD | Decimal | Potential annual premium. |
| DaysSinceLeadCreated | Integer | Lead age. |
| LeadStage | Text | Current open stage, for action filtering only. |
| ConversionProbability | Decimal | Model probability from 0 to 1. |
| PredictedConvertedFlag | Integer flag | Probability at or above 0.5. |
| PropensityBand | Text | High `>=0.65`, Medium `>=0.35`, otherwise Low. |
| ModelVersion | Text | Selected algorithm and synthetic model version. |
| ScoredAt | Timestamp | Batch score timestamp. |
