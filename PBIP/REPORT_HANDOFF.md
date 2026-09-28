# Report handoff

Open `InsuranceDemoSM.pbip` in Power BI Desktop. Five 1600 x 900 pages use the existing Direct Lake model, explicit measures, a shared theme and page navigation. The report connection and Fabric partitions are unchanged.

## Semantic-model fixes restored in this version

- Corrected the policy/customer relationship so the policy foreign key points to the customer dimension key.
- Corrected application and lead-created relationships to use the matching date columns (`ApplicationDate`/`LeadCreatedDate` to `gold_dim_date[Date]`). The Fabric SQL endpoint currently exposes the corresponding `*DateKey` fields as `date`, while `DateKey` is `Int64`, so key-to-key relationships would not match.
- Activated lead-conversion product and agent relationships.
- Added explicit `Scored Leads` and `Avg Lead Age Days` measures for AI visuals.
- Updated `Target Attainment` to count only months represented by policy rows instead of every month in the full date dimension.
- The existing Boolean measures continue to compare their flags to `TRUE()`.

`IssueDateKey` and `RenewalDateKey` remain without role-playing relationships because Direct Lake currently exposes them as `DateTime`, while `gold_dim_date[DateKey]` is `Int64`. Adding those relationships prevents the PBIP from opening. Convert/reframe those two Lakehouse fields as whole-number keys before adding the inactive relationships later.

## Manual verification

- Check Fabric credentials, data availability, source key types, KPI totals and all relationships before presenting.
- Ctrl-click navigation buttons in Desktop edit mode; verify slicer synchronization and the Time Intelligence selection.
- Enable the native map visual if tenant/Desktop settings disable maps. Its coordinates are planning-area centroids.
- Inspect matrix expansion, conditional colors, table widths, legends and chart rendering at Fit to page.
- The existing YoY % calculation item has no dynamic percentage format string. Verify its numeric display when applied to currency/count measures.
- AI score distribution plots probability against the explicit average lead-age measure, one dot per scored lead. The band chart uses the explicit `Scored Leads` measure.
- The lead pipeline is a sorted bar chart of current stage populations, not a historical cumulative funnel. The model contains no stage-event history.
- Overview and AI region slicers use the agent/business region so they can filter the shared agent dimension after the relationships are valid.
- Target attainment now derives its month count from policy activity; still test custom date selections and no-data contexts.

The report was edited as PBIR files. Live Direct Lake rendering was not executed as part of these file changes.

Lightweight checks passed for all five pages and 136 visual containers: exact TMDL field/measure references, page-navigation targets and canvas bounds. Re-run the online Microsoft JSON-schema check after any Desktop save.
