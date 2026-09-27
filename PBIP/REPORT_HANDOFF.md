# Report handoff

Open `InsuranceDemoSM.pbip` in Power BI Desktop. Five 1600 x 900 pages use the existing Direct Lake model, explicit measures, a shared theme and page navigation. The report connection and Fabric partitions are unchanged.

## Small semantic-model fix

Four existing measures compared Boolean fields to the integer 1. `Renewal Rate`, `Lapse Rate`, `Converted Leads` and `Active Agents` now compare their flags to `TRUE()`. No measures were added.

## Existing model issues requiring Desktop review

The report files cannot correct these existing model relationships. They were left unchanged under the requested model-edit restrictions:

- `gold_lead_conversion.LeadCreatedDateKey` currently joins to `gold_dim_customer.CustomerKey`, rather than `gold_dim_date.DateKey`. Customer filtering can therefore remove the lead population.
- The lead conversion relationships to product and agent are inactive. Agent conversion rates and response hours may repeat across agents; product/channel/date slicers may not filter leads correctly.
- The customer/policy relationship is stored with `gold_dim_customer.CustomerKey` on the from side and `gold_fact_policy.CustomerKey` on the to side, without explicit cardinalities. Verify customer = one, policy = many and dimension-to-fact filtering.
- `IssueDateKey` and `RenewalDateKey` are typed as dateTime, and their role-playing date relationships are absent. The report uses the existing application-date relationship.

## Manual verification

- Check Fabric credentials, data availability, KPI totals and the relationship issues above before presenting.
- Ctrl-click navigation buttons in Desktop edit mode; verify slicer synchronization and the Time Intelligence selection.
- Enable the native map visual if tenant/Desktop settings disable maps. Its coordinates are planning-area centroids.
- Inspect matrix expansion, conditional colors, table widths, legends and chart rendering at Fit to page.
- The existing YoY % calculation item has no dynamic percentage format string. Verify its numeric display when applied to currency/count measures.
- AI score distribution plots probability against lead age, one dot per scored lead. The band chart uses a distinct count of scored LeadID because the model has no explicit scored-lead count measure; the remaining aggregate bindings use existing measures.
- The lead funnel shows current stage populations, not historical cumulative stage transitions. The model contains no stage-event history.
- Default date selection includes the model's full date dimension. Select the intended business months for target attainment and time calculations; future renewal-calendar dates can dilute the target denominator.

The report was edited as PBIR files. Live Direct Lake rendering was not executed as part of these file changes.

Lightweight checks passed for all five pages and 116 visual containers: official Microsoft JSON schemas, exact TMDL field/measure references, page-navigation targets and canvas bounds.
