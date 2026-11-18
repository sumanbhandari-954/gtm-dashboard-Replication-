# Weekly refresh — GTM dashboard replica

Run every Monday, or by hand. It refreshes the Salesforce aggregates, rebuilds the page and checks it.
Plan targets come from the slow tier and are not refreshed weekly.

## 1. Pull the Salesforce aggregates

Run each SOQL below with the Salesforce connector and paste the records into the matching block of
`replica/data_2026.json` (bookings, churn, open, ownerWon) or `replica/salesforce_2026_extra.json`
(cohort, renewalStatusOpen, cycle, openStages2026, topAccounts). Aggregates only. Never paste raw
opportunity rows. Set `asOf` in both files to today's date.

| Block | File | SOQL |
|---|---|---|
| won, churn | data_2026.json | `SELECT CALENDAR_QUARTER(CloseDate) q, Type t, IsWon w, COUNT(Id) n, SUM(Deal_ARR__c) arr, SUM(Churn_Amount__c) churn FROM Opportunity WHERE CloseDate >= 2026-01-01 AND CloseDate <= 2026-12-31 AND Type != 'Migration' AND Deal_ARR__c > 0 AND IsClosed = true GROUP BY CALENDAR_QUARTER(CloseDate), Type, IsWon` |
| open | data_2026.json | `SELECT CALENDAR_QUARTER(CloseDate) q, ForecastCategoryName fc, Type t, COUNT(Id) n, SUM(Deal_ARR__c) arr FROM Opportunity WHERE CloseDate >= 2026-01-01 AND CloseDate <= 2026-12-31 AND Type != 'Migration' AND Deal_ARR__c > 0 AND IsClosed = false GROUP BY CALENDAR_QUARTER(CloseDate), ForecastCategoryName, Type` |
| ownerWon | data_2026.json | `SELECT OwnerId, CALENDAR_QUARTER(CloseDate) q, Type t, SUM(Deal_ARR__c) arr, COUNT(Id) n FROM Opportunity WHERE CloseDate >= 2026-01-01 AND CloseDate <= 2026-12-31 AND Type IN ('New Business','Upsell') AND Deal_ARR__c > 0 AND IsWon = true GROUP BY OwnerId, CALENDAR_QUARTER(CloseDate), Type` then resolve names: `SELECT Id, Name FROM User WHERE Id IN (...)` |
| cohort | salesforce_2026_extra.json | `SELECT CALENDAR_QUARTER(Sales_Cycle_Create_Date__c) q, Type t, Attribution__c a, COUNT(Id) n, SUM(Deal_ARR__c) arr FROM Opportunity WHERE Sales_Cycle_Create_Date__c >= 2026-01-01 AND Sales_Cycle_Create_Date__c <= 2026-12-31 AND Type != 'Migration' AND Deal_ARR__c > 0 GROUP BY CALENDAR_QUARTER(Sales_Cycle_Create_Date__c), Type, Attribution__c` |
| renewalStatusOpen | salesforce_2026_extra.json | `SELECT CALENDAR_QUARTER(CloseDate) q, Overall_Renewal_Status__c s, COUNT(Id) n, SUM(Deal_ARR__c) arr FROM Opportunity WHERE CloseDate >= 2026-01-01 AND CloseDate <= 2027-12-31 AND Type = 'Renewal (Flat or Partial Churn)' AND Deal_ARR__c > 0 AND IsClosed = false GROUP BY CALENDAR_QUARTER(CloseDate), Overall_Renewal_Status__c` |
| cycle | salesforce_2026_extra.json | `SELECT CALENDAR_QUARTER(CloseDate) q, Type t, COUNT(Id) n, AVG(Sales_Cycle_Days__c) cyc FROM Opportunity WHERE CloseDate >= 2026-01-01 AND CloseDate <= 2026-12-31 AND IsWon = true AND Type IN ('New Business','Upsell') AND Deal_ARR__c > 0 GROUP BY CALENDAR_QUARTER(CloseDate), Type` |
| openStages2026 | salesforce_2026_extra.json | `SELECT StageName s, COUNT(Id) n, SUM(Deal_ARR__c) arr FROM Opportunity WHERE IsClosed = false AND Type != 'Migration' AND Deal_ARR__c > 0 AND CloseDate >= 2026-01-01 AND CloseDate <= 2026-12-31 GROUP BY StageName` |
| topAccounts | salesforce_2026_extra.json | `SELECT Id, Name, Account_ARR__c, Industry FROM Account WHERE Account_ARR__c > 0 ORDER BY Account_ARR__c DESC LIMIT 25` |

## 2. Build

```bash
cd <project root>
python3 replica/build_dashboard.py
```

It prints bookings, churn, roll-forward, open pipeline and overdue renewals. Check that they moved
sensibly against last week. Large swings mean a bad pull: stop and look before publishing.

## 3. Check

Open `replica/replica_dashboard.html` in headless Chromium. Click through all six tabs and confirm there
are no page errors and no horizontal overflow at 1100px.

## 4. Publish

Commit only the files under `replica/` and push to the agreed branch. Do not push anything else.
The page can also be published as a private Artifact.

## Known limits

- Plan and quota figures come from the slow tier, which is refreshed locally, so they can be up to
  100 days old. The page states the as-of date.
- Open renewals with a past close date are counted as overdue and show as a data-quality flag. This
  is a finding about the data, not a bug in the build.
- NRR, GRR, partner scorecard, Demand Gen, landing pages, Pipeline Productivity and Customer Health are not
  built yet.
