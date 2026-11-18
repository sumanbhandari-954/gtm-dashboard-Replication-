# GTM Dashboard — replica

A partial replica of the GTM Executive Dashboard, built from data that can be reached today.

- `data_2026.json` — 2026 Salesforce Opportunity aggregates (scope and as-of date stored in the file).
- `build_replica.py` — computes bookings vs plan, churn vs allowance, open pipeline by forecast category and rep attainment, then writes `replica_dashboard.html`.
- `replica_dashboard.html` — the built page (self-contained, no external requests).

The plan targets come from `data/slow/` in `striimvirani/gtm-dashboard` (parsed from the Reporting Data Warehouse workbook). `build_replica.py` reads `../data/slow/sheet_targets.json` and `../data/slow/sheet_arr_rollforward.json`, so this repo's files need that folder layout to rebuild. The built page is included, so it can be viewed without rebuilding.

Not yet covered: NRR/GRR, partner channel, Demand Gen, sales productivity, pipeline productivity, customer health, top accounts, stage-conversion ladders.
