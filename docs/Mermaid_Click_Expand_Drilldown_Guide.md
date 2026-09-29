# Mermaid Flowchart — Same-File Click Drill-down Guide

> Goal: **Mermaid flowchart node-ஐ click செய்தால், இதே Markdown file-ல் இருக்கும் detailed flow section-க்கு route ஆக வேண்டும்.**

இந்த version-ல் `<details>` expand/collapse-ஐ main approach ஆக பயன்படுத்தவில்லை. அதற்கு பதிலாக Mermaid `click` directive + same-file heading anchors பயன்படுத்தப்படுகிறது.

---

# 1. Main Flow — Nodes are Clickable

கீழே இருக்கும் `Process Order`, `Wait for Payment`, `Cancel Order` nodes-ஐ click செய்தால் இந்த same `.md` file-ல் இருக்கும் respective detailed section-க்கு செல்லும்.

```mermaid
flowchart TD
    A[Order Received] --> B{Payment Status}
    B -->|Paid| C[Process Order]
    B -->|Pending| D[Wait for Payment]
    B -->|Failed| E[Cancel Order]

    click C "https://github.com/mani-baskar/Daiichi-Life-Demo-Report/blob/main/docs/Mermaid_Click_Expand_Drilldown_Guide.md#process-order-details" "Open Process Order Details" _self
    click D "https://github.com/mani-baskar/Daiichi-Life-Demo-Report/blob/main/docs/Mermaid_Click_Expand_Drilldown_Guide.md#wait-for-payment-details" "Open Wait for Payment Details" _self
    click E "https://github.com/mani-baskar/Daiichi-Life-Demo-Report/blob/main/docs/Mermaid_Click_Expand_Drilldown_Guide.md#cancel-order-details" "Open Cancel Order Details" _self
```

Fallback links:

- [Process Order Details](#process-order-details)
- [Wait for Payment Details](#wait-for-payment-details)
- [Cancel Order Details](#cancel-order-details)

---

# 2. Process Order Details

```mermaid
flowchart TD
    P1[Validate Order]
    P2[Check Inventory]
    P3{Stock Available?}
    P4[Reserve Stock]
    P5[Generate Invoice]
    P6[Pack Product]
    P7[Ship Order]
    P8[Notify Out of Stock]

    P1 --> P2 --> P3
    P3 -->|Yes| P4 --> P5 --> P6 --> P7
    P3 -->|No| P8
```

[⬆ Back to Main Flow](#1-main-flow--nodes-are-clickable)

---

# 3. Wait for Payment Details

```mermaid
flowchart TD
    W1[Payment Pending]
    W2[Send Reminder]
    W3{Payment Received?}
    W4[Continue Order]
    W5{Timeout Reached?}
    W6[Cancel Order]

    W1 --> W2 --> W3
    W3 -->|Yes| W4
    W3 -->|No| W5
    W5 -->|No| W2
    W5 -->|Yes| W6
```

[⬆ Back to Main Flow](#1-main-flow--nodes-are-clickable)

---

# 4. Cancel Order Details

```mermaid
flowchart TD
    C1[Mark Order Cancelled]
    C2[Release Reserved Stock]
    C3[Write Audit Log]
    C4[Notify Customer]
    C5[Close Order]

    C1 --> C2 --> C3 --> C4 --> C5
```

[⬆ Back to Main Flow](#1-main-flow--nodes-are-clickable)

---

# 5. How Same-File Routing Works

Mermaid syntax:

```mermaid
flowchart LR
    A[Main Step] --> B[Detailed Step]
    click B "https://github.com/mani-baskar/Daiichi-Life-Demo-Report/blob/main/docs/Mermaid_Click_Expand_Drilldown_Guide.md#6-detailed-step-example" "Open Detailed Step" _self
```

Important parts:

```text
click B "FULL_SAME_FILE_URL#heading-anchor" "Tooltip" _self
```

- `B` = clickable node ID.
- URL = இதே Markdown file URL.
- `#heading-anchor` = கீழே இருக்கும் heading-ன் GitHub anchor.
- `_self` = same browser tab-ல் open செய்ய முயலும்.

GitHub heading:

```markdown
## Detailed Step Example
```

அதன் anchor பொதுவாக:

```text
#detailed-step-example
```

---

# 6. Detailed Step Example

```mermaid
flowchart TD
    D1[Read Input] --> D2[Validate]
    D2 --> D3{Valid?}
    D3 -->|Yes| D4[Process]
    D3 -->|No| D5[Return Error]
```

[⬆ Back to Main Flow](#1-main-flow--nodes-are-clickable)

---

# 7. Reusable Template

இந்த pattern-ஐ வேறு project-க்கும் reuse செய்யலாம்.

```markdown
## Main Flow

```mermaid
flowchart TD
    A[Start] --> B[Process A]
    B --> C[Process B]

    click B "FULL_MD_FILE_URL#process-a-details" "Open Process A" _self
    click C "FULL_MD_FILE_URL#process-b-details" "Open Process B" _self
```

## Process A Details

```mermaid
flowchart TD
    A1[Sub Step A1] --> A2[Sub Step A2]
```

[Back to Main Flow](#main-flow)

## Process B Details

```mermaid
flowchart TD
    B1[Sub Step B1] --> B2[Sub Step B2]
```
```

---

# 8. Power BI Same-File Drill-down Example

```mermaid
flowchart LR
    BQ[(BigQuery)] --> PQ[Power Query]
    PQ --> MODEL[Semantic Model]
    MODEL --> REPORT[Power BI Report]
    REPORT --> SERVICE[Power BI Service]

    click PQ "https://github.com/mani-baskar/Daiichi-Life-Demo-Report/blob/main/docs/Mermaid_Click_Expand_Drilldown_Guide.md#9-power-query-details" "View Power Query Flow" _self
    click MODEL "https://github.com/mani-baskar/Daiichi-Life-Demo-Report/blob/main/docs/Mermaid_Click_Expand_Drilldown_Guide.md#10-semantic-model-details" "View Semantic Model Flow" _self
```

Fallback:

- [Power Query Details](#9-power-query-details)
- [Semantic Model Details](#10-semantic-model-details)

---

# 9. Power Query Details

```mermaid
flowchart TD
    A[Connect BigQuery]
    B[Filter Rows]
    C[Change Data Types]
    D[Merge Queries]
    E[Business Transformations]
    F[Load to Model]

    A --> B --> C --> D --> E --> F
```

[⬆ Back to Power BI Main Flow](#8-power-bi-same-file-drill-down-example)

---

# 10. Semantic Model Details

```mermaid
flowchart TD
    A[Load Tables]
    B[Create Relationships]
    C[Create DAX Measures]
    D[Validate Totals]
    E[Ready for Report]

    A --> B --> C --> D --> E
```

[⬆ Back to Power BI Main Flow](#8-power-bi-same-file-drill-down-example)

---

# 11. Important Limitation

இந்த approach:

```text
Node click
   ↓
Same Markdown file
   ↓
Detailed section
   ↓
Detailed Mermaid flow
```

என்று **navigation-based drill-down** தரும்.

ஆனால்:

```text
Node click
   ↓
Same Mermaid diagram dynamically expands
   ↓
Child nodes appear inside the same graph
```

இந்த true inline expansion GitHub Markdown + native Mermaid மட்டும் வைத்து கிடையாது.

மேலும் Mermaid `click` interaction renderer/security configuration-ஐ பொறுத்து disable ஆகலாம். அதனால்தான் ஒவ்வொரு diagram கீழேயும் normal Markdown fallback links வைத்திருக்கிறோம்.

---

# 12. Correct `click` Syntax

External URL:

```mermaid
flowchart LR
    A[GitHub]
    click A "https://github.com" "Open GitHub" _self
```

Same file section:

```text
click NODE "https://github.com/OWNER/REPO/blob/main/path/file.md#section-anchor" "View Details" _self
```

Incorrect:

```text
click A "[https://github.com](https://github.com)"
```

Mermaid `click` URL-க்குள் Markdown link syntax போட வேண்டாம்.

---

# 13. Recommended Documentation Pattern

```text
High-Level Mermaid
     │
     ├── click node → Detail Section A
     │                   ↓
     │              Detailed Mermaid
     │                   ↓
     │              Back to Main Flow
     │
     ├── click node → Detail Section B
     │                   ↓
     │              Detailed Mermaid
     │
     └── click node → Detail Section C
```

இந்த approach `.md` documentation-ல் high-level diagram clean-ஆ வைத்துக்கொண்டு, தேவையான detail-க்கு drill-down navigation கொடுக்க useful.