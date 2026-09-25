# 04 - Power BI Live Demo Design for Interview

## Goal

Interview-la report attractive-a irukkanum. Aana main objective:

**"I can take Azure/Fabric data and convert it into a governed, decision-ready Power BI solution."**

Report title:

**Life Insurance Growth & Customer Analytics**

Subtitle:

**Synthetic Azure + Fabric + Power BI Demonstration**

Do not use Daiichi logo unless permission.
Do not call data "Daiichi data".

---

# Total Pages

**5 pages** enough:

1. Executive Overview
2. Policy & Product Performance
3. Customer & Geography
4. Distribution / Agent Performance
5. AI Lead Conversion

5 pages-ku mela live interview-la navigation time waste aagum.

---

# Page 1 - Executive Overview

## Purpose
Management 30 seconds-la business health understand pannanum.

## KPI Cards
- Active Policies
- Annual Premium SGD
- New Policies
- Renewal Rate
- Lead Conversion Rate
- Lapse Rate

## Visual 1 - Monthly Premium + Policies
Visual:
- Line and clustered column
- Column = Premium / New Premium
- Line = Policy Count

Why:
Growth + volume same visual-la.

## Visual 2 - Lead Funnel
Stages:
- Lead
- Qualified
- Quote
- Application
- Won

Why:
Sales leakage enga irukku nu theriyum.

## Visual 3 - Channel Mix
- Agency
- Bancassurance
- Digital
- Broker / IFA
- Direct

Visual:
- Bar or donut

## Visual 4 - Product Mix
Horizontal bar:
- Premium by Product Family

## Slicers
- Date
- Region
- Product Family
- Channel

---

# Page 2 - Policy & Product Performance

## Purpose
Which product grows? Which product lapses? Risk/performance epadi?

## KPI
- Total Policies
- Avg Annual Premium
- Total Sum Assured
- Renewal Rate
- Claim Rate
- Avg Days to Issue

## Product Performance Matrix
Rows:
- Product Family
- Product Name

Values:
- Policies
- Premium
- Avg Premium
- Renewal Rate
- Lapse Rate
- Claim Rate

Conditional formatting use pannunga.

## Premium Trend by Product
- Small multiples line chart or stacked column

## Premium vs Sum Assured
Scatter:
- X = Avg Premium
- Y = Avg Sum Assured
- Size = Policies
- Legend = Product Family

## Policy Status
Stacked bar:
- Active
- Lapsed
- Matured
- Claimed

## Time Intelligence
Calculation Group slicer:
- MTD
- QTD
- YTD
- PY
- YoY %

Interview-la Calculation Group live-a show panna impact irukkum.

---

# Page 3 - Customer & Geography

## Purpose
Customer profile + geography + retention.

## Singapore Map
Use:
- PlanningAreaLatitude
- PlanningAreaLongitude
- Bubble size = Policies or Premium
- Tooltip = Customers, Premium, Conversion, Renewal

Why:
Map requirement cover pannum.
Exact household location use panna koodadhu.

## Customer Segment
Bar:
- Emerging
- Mass
- Affluent
- High Value

## Age Band vs Product
- 100% stacked bar or matrix

## Income Band vs Premium
- Column chart

## Existing vs New Customer
- Conversion
- Avg Premium

## Retention View
- Lapse Rate by Region / Segment

Talking point:

> "Geographic analysis is aggregated to planning-area level rather than plotting exact customer locations, which is more privacy-appropriate."

---

# Page 4 - Distribution / Agent Performance

## Purpose
Sales/distribution performance manage panna.

## KPI
- Active Agents
- Premium per Agent
- Policies per Agent
- Conversion Rate
- Target Attainment
- Avg First Response Hours

## Agent Leaderboard
Columns:
- Agent
- Channel
- Premium
- Policies
- Conversion
- Renewal
- Target %
- Rank

## Conversion vs Premium Scatter
- X = Conversion Rate
- Y = Premium
- Size = Policies
- Legend = Channel

Purpose:
High-value + high-conversion performers identify panna.

## Channel Funnel
Lead -> Quote -> Application -> Won
Breakdown by channel.

## Target Attainment
- Actual vs Target bar/bullet style

## Branch / Region Comparison
- Horizontal bar / small multiples

---

# Page 5 - AI Lead Conversion

## Purpose
Notebook prediction-ai business action-aa convert pannradhu.

## KPI
- Open Leads
- High Propensity Leads
- Avg Conversion Probability
- Expected Conversions
- Potential Premium from High Propensity Leads

## Propensity Band
Bar:
- High
- Medium
- Low

## Top Leads Table
Columns:
- LeadID
- Product Interest
- Channel
- Region
- Estimated Premium
- Conversion Probability
- Propensity Band
- Days Since Lead
- Assigned Agent

Conditional formatting:
- Probability data bar
- High/Medium/Low icon

## Probability Distribution
- Histogram / binned column

## High Propensity by Channel
- Stacked bar

## High Propensity by Product
- Bar chart

## Action View
Filter:
- `PropensityBand = High`
- LeadStage not in Won/Lost

This becomes sales priority queue.

---

# Core DAX Measures

Create at least:

```text
[Total Policies]
[Active Policies]
[Annual Premium]
[Average Premium]
[Total Sum Assured]
[Renewal Rate]
[Lapse Rate]
[Claim Rate]
[Average Days To Issue]

[Total Leads]
[Converted Leads]
[Conversion Rate]
[Open Leads]
[High Propensity Leads]
[Average Conversion Probability]
[Expected Conversions]
[Potential Premium - High Propensity]
```

Avoid too many calculated columns.
Business aggregation mostly measures-la.

---

# Calculation Group

Name:

`Time Intelligence`

Items:
- Current
- MTD
- QTD
- YTD
- Previous Month
- Previous Year
- YoY %

Use with:
- Annual Premium
- Policies
- Leads
- Converted Leads

---

# UI / Theme

Professional insurance/financial-services style.

Guidelines:
- White/light neutral canvas
- Dark navy headings
- Blue/teal primary data accents
- One warm accent for attention
- Red only for negative exception/lapse
- Consistent corner radius
- Consistent title position
- Grid alignment
- Consistent spacing
- Avoid visual overload

**Consistency > fancy effects**

---

# Navigation

Separate Home page thevai illa.

Page 1 header buttons:

```text
Overview | Products | Customers | Distribution | AI Leads
```

Total visible pages = 5.

Optional Power BI App-la later polished landing page create pannalaam.

---

# Tooltip / Drillthrough

Optional hidden tooltip:

`TT_ProductDetail`

Show:
- Premium
- Policies
- Renewal
- Lapse
- Avg Premium
- YoY %

Optional drillthrough:

`DT_AgentDetail`

Time illa skip pannunga.

---

# Model Performance Talking Points

- Star schema
- Single-direction relationship default
- Correct data types
- High-cardinality unnecessary columns remove
- Measures over repeated calculated columns
- Unused columns remove
- Direct Lake
- DAX variables
- Iterator only when needed
- Performance Analyzer

---

# RLS Talking Point

Live configure mandatory illa.

Scenario:
- Regional manager = own region
- Distribution manager = own channel
- Executive = all

Implementation:
- Entra group / user-region mapping
- Dynamic RLS if needed

Security table add pannina source-table count change aagum; so live source demo-la optional architecture talking point-aa vechukonga.

---

# Live Demo Script - 8 Minutes

## 0:00 - 0:45
Opening:

> "I built a small synthetic life-insurance solution specifically to demonstrate the Azure, Fabric and Power BI flow in the JD. No real customer data is used."

## 0:45 - 1:45
Architecture:
- Azure SQL
- ADF
- ADLS
- OneLake Shortcut
- Lakehouse
- Direct Lake
- Power BI

## 1:45 - 2:30
Fabric:
- Lakehouse
- Pipeline
- Silver/Gold tables

## 2:30 - 3:15
Notebook:
- model training
- metrics
- scored output

Do not explain every code cell.

## 3:15 - 6:30
Power BI:
- Overview
- Product
- Geography
- Agent
- AI Lead page

## 6:30 - 7:15
Show:
- Calculation Group
- Direct Lake semantic model

## 7:15 - 8:00
Close:
- Dev/Test/Prod deployment
- security/governance
- ask where their current architecture differs

---

# Questions Demo Should Trigger

Expected:
- Why Lakehouse instead of Warehouse?
- Why Shortcut instead of Copy?
- Why Direct Lake?
- Incremental load epadi?
- Dev/Test/Prod epadi?
- RLS epadi?
- Model retraining epadi?
- Lead scoring fairness epadi?
- Existing Azure SQL/ADF environment Fabric-ku epadi integrate pannuveenga?

Intha questions varradhu positive. Demo technical discussion-ai guide pannum.

---

# Final Interview Message

> "I kept the solution deliberately small enough to demonstrate live, but the architecture is scalable: the source and landing layer are separated, Fabric handles governed transformation and data science, the semantic model centralizes business logic, and Power BI provides the business consumption layer. In production I would add the required private networking, security, governance and deployment controls."

---

# Best Prediction Approach

**Fabric Notebook dhaan use pannunga.**

Azure ML / AutoML possible, but intha interview-ku unnecessary complexity.

Cleanest path:

**Fabric Notebook -> scored Delta table -> Direct Lake -> Power BI AI Lead page**

Benefits:
- same platform
- same Lakehouse
- Python
- MLflow
- batch scoring
- direct BI consumption
