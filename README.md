# GTM Dashboard — replica

A partial replica of the GTM Executive Dashboard, built from data that can be reached today.

- `data_2026.json` — 2026 Salesforce Opportunity aggregates (scope and as-of date stored in the file).
- `build_replica.py` — computes bookings vs plan, churn vs allowance, open pipeline by forecast category and rep attainment, then writes `replica_dashboard.html`.
- `replica_dashboard.html` — the built page (self-contained, no external requests).

The plan targets are read from `data/slow/` in the source project (parsed from the Reporting Data Warehouse workbook). This repo ships a copy of the Salesforce aggregates and the built page; `build_replica.py` expects the plan-target JSON files alongside it in the same layout, as in `striimvirani/gtm-dashboard`.

Not yet covered: NRR/GRR, partner channel, Demand Gen, sales productivity, pipeline productivity, customer health, top accounts, stage-conversion ladders.
