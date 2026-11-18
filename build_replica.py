#!/usr/bin/env python3
"""Replica of the GTM Executive Dashboard, built from the data that is reachable today.

Inputs
  replica/data_2026.json          Salesforce aggregates (scope and date stamped inside the file)
  data/slow/sheet_targets.json    plan targets parsed from the Reporting Data Warehouse workbook
  data/slow/sheet_arr_rollforward.json   Beginning ARR (Jan-26) from the same workbook

Output
  replica/replica_dashboard.html  one self-contained page, no external requests

Run:  python3 replica/build_replica.py
"""
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D = json.load(open(os.path.join(HERE, 'data_2026.json')))
T = json.load(open(os.path.join(ROOT, 'data', 'slow', 'sheet_targets.json')))
RF = json.load(open(os.path.join(ROOT, 'data', 'slow', 'sheet_arr_rollforward.json')))
OUT = os.path.join(HERE, 'replica_dashboard.html')

QS = ['2026-Q1', '2026-Q2', '2026-Q3', '2026-Q4']
QLBL = {'2026-Q1': 'Q1', '2026-Q2': 'Q2', '2026-Q3': 'Q3', '2026-Q4': 'Q4'}
CLOSED_Q = ['2026-Q1', '2026-Q2', '2026-Q3']          # Q4 is in progress on the as-of date
esc = lambda s: html.escape(str(s))


def m(v, d=2):
    return f'${v / 1e6:,.{d}f}M'


def k(v):
    return f'${v / 1e3:,.0f}K'


def pct(a, b):
    return f'{100 * a / b:,.0f}%' if b else '—'


# ── bookings and plan ─────────────────────────────────────────────────────────
won_new = {q: D['won'][q]['New Business'] for q in QS}
won_up = {q: D['won'][q]['Upsell'] for q in QS}
won_ren = {q: D['won'][q]['Renewal'] for q in QS}
plan_new = {q: T['quarterly'][q]['new'] for q in QS}
plan_up = {q: T['quarterly'][q]['upsell'] for q in QS}
plan_tot = {q: T['quarterly'][q]['total'] for q in QS}
tol = {q: -T['quarterly'][q]['churnTolerance'] for q in QS}          # planned churn allowance, positive

ytd_new = sum(won_new[q] for q in QS)
ytd_up = sum(won_up[q] for q in QS)
ytd_bookings = ytd_new + ytd_up
fy_plan = T['annual']['total']
closed_plan = sum(plan_tot[q] for q in CLOSED_Q)
closed_actual = sum(won_new[q] + won_up[q] for q in CLOSED_Q)

# ── churn ─────────────────────────────────────────────────────────────────────
churn = {q: D['churn'][q]['lost'] + D['churn'][q]['wonChurn'] for q in QS}
ytd_churn = sum(churn.values())

# ── ARR (simple roll-forward; excludes renewal uplift, so it is not the published figure) ──
beg_arr = float(RF['monthly']['Beginning ARR']['total'].replace(',', '')) * 1000
roll_arr = beg_arr + ytd_new + ytd_up - ytd_churn

# ── open pipeline by forecast category (2026 close dates only) ─────────────────
FC_ORDER = ['Commit', 'Best Case', 'Stretch', 'Omitted']
open_by_fc = {f: 0.0 for f in FC_ORDER}
for r in D['open']:
    open_by_fc[r['fc']] += r['arr']
open_total = sum(open_by_fc.values())

# ── rep attainment ────────────────────────────────────────────────────────────
reps = {}
for r in D['ownerWon']:
    reps.setdefault(r['owner'], 0.0)
    reps[r['owner']] += r['arr']
rep_rows = []
for name, booked in reps.items():
    quota = T['quotas'].get(name)
    rep_rows.append((name, booked, quota))
rep_rows.sort(key=lambda x: -x[1])

# ── HTML ──────────────────────────────────────────────────────────────────────
CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#14181f;--mut:#6b7280;--line:#e5e7eb;--new:#1f4e9c;--up:#2e9c86;--ren:#8c6bd1;--warn:#b42318;--ok:#067647}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#0f1319;--card:#171c25;--ink:#e8ebf1;--mut:#9aa3b2;--line:#262d39;--new:#7aa7ff;--up:#4fd1b5;--ren:#b9a2f0;--warn:#ff8a80;--ok:#6ee7a8}}
:root[data-theme="dark"]{--bg:#0f1319;--card:#171c25;--ink:#e8ebf1;--mut:#9aa3b2;--line:#262d39;--new:#7aa7ff;--up:#4fd1b5;--ren:#b9a2f0;--warn:#ff8a80;--ok:#6ee7a8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 60px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:32px 0 10px}.sub{color:var(--mut);margin:0 0 18px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.kpi,.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.kpi b{display:block;font-size:22px;margin-top:4px}.kpi span{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.kpi small{color:var(--mut)}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:right}
th:first-child,td:first-child{text-align:left}th{color:var(--mut);font-weight:600;font-size:12px}
.bar{height:10px;border-radius:5px;background:var(--line);overflow:hidden;min-width:120px}.bar i{display:block;height:100%}
.legend{color:var(--mut);font-size:12px;margin:6px 0 0}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px 0 12px;vertical-align:-1px}
.note{color:var(--mut);font-size:12px;margin-top:8px}.neg{color:var(--warn)}.pos{color:var(--ok)}
.q{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
@media (max-width:640px){.q{grid-template-columns:1fr 1fr}}
"""


def stack_bars(series_list, scale):
    """series_list: list of (color, value); stacked horizontal bar."""
    out = []
    for color, v in series_list:
        out.append(f'<i style="width:{100 * v / scale:.1f}%;background:{color};display:inline-block;height:100%"></i>')
    return '<div class="bar" style="display:flex">' + ''.join(out) + '</div>'


def quarter_cards():
    cards = []
    for q in QS:
        act = won_new[q] + won_up[q]
        plan = plan_tot[q]
        scale = max(plan, act, 1)
        status = 'closed' if q in CLOSED_Q else 'in progress'
        cards.append(f'''<div class="card"><div style="color:var(--mut);font-size:12px">{QLBL[q]} 2026 · {status}</div>
<b style="font-size:20px">{m(act)}</b> <span style="color:var(--mut)">of {m(plan, 1)} plan</span>
<div style="margin:8px 0">{stack_bars([('var(--new)', won_new[q]), ('var(--up)', won_up[q])], scale)}</div>
<div style="color:var(--mut);font-size:12px">{pct(act, plan)} attained · new {m(won_new[q])} · upsell {m(won_up[q])}</div></div>''')
    return '<div class="q">' + ''.join(cards) + '</div>'


def bookings_table():
    rows = []
    for q in QS:
        act = won_new[q] + won_up[q]
        rows.append(f'<tr><td>{QLBL[q]}</td><td>{k(plan_new[q])}</td><td>{k(won_new[q])}</td>'
                    f'<td>{k(plan_up[q])}</td><td>{k(won_up[q])}</td><td>{k(plan_tot[q])}</td>'
                    f'<td>{k(act)}</td><td>{pct(act, plan_tot[q])}</td></tr>')
    rows.append(f'<tr><td><b>FY</b></td><td>{k(T["annual"]["new"])}</td><td>{k(ytd_new)}</td>'
                f'<td>{k(T["annual"]["upsell"])}</td><td>{k(ytd_up)}</td><td>{k(fy_plan)}</td>'
                f'<td>{k(ytd_bookings)}</td><td>{pct(ytd_bookings, fy_plan)}</td></tr>')
    return ('<table><thead><tr><th>Quarter</th><th>New plan</th><th>New won</th><th>Upsell plan</th>'
            '<th>Upsell won</th><th>Total plan</th><th>Total won</th><th>Attained</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table>')


def churn_table():
    rows = []
    for q in QS:
        over = churn[q] > tol[q]
        cls = 'neg' if over else 'pos'
        rows.append(f'<tr><td>{QLBL[q]}</td><td>{k(D["churn"][q]["lost"])}</td><td>{k(D["churn"][q]["wonChurn"])}</td>'
                    f'<td>{k(churn[q])}</td><td>{k(tol[q])}</td><td class="{cls}">{"over" if over else "within"}</td>'
                    f'<td>{k(won_ren[q])}</td></tr>')
    rows.append(f'<tr><td><b>YTD</b></td><td></td><td></td><td>{k(ytd_churn)}</td>'
                f'<td>{k(sum(tol[q] for q in QS))}</td><td></td><td>{k(sum(won_ren.values()))}</td></tr>')
    return ('<table><thead><tr><th>Quarter</th><th>Lost renewals</th><th>Churn on won renewals</th>'
            '<th>Total churn</th><th>Planned allowance</th><th>vs allowance</th><th>Renewals won (ARR)</th></tr></thead>'
            '<tbody>' + ''.join(rows) + '</tbody></table>')


def forecast_table():
    rows = []
    maxv = max(open_by_fc.values()) or 1
    for f in FC_ORDER:
        rows.append(f'<tr><td>{f}</td><td>{m(open_by_fc[f])}</td><td style="width:45%">'
                    f'{stack_bars([("var(--new)", open_by_fc[f])], maxv)}</td></tr>')
    rows.append(f'<tr><td><b>Total open</b></td><td><b>{m(open_total)}</b></td><td></td></tr>')
    return ('<table><thead><tr><th>Forecast category</th><th>Open ARR (2026 close)</th><th></th></tr></thead>'
            '<tbody>' + ''.join(rows) + '</tbody></table>')


def rep_table():
    rows = []
    for name, booked, quota in rep_rows:
        att = pct(booked, quota) if quota else '—'
        qtxt = m(quota) if quota else 'no quota on file'
        rows.append(f'<tr><td>{esc(name)}</td><td>{m(booked)}</td><td>{qtxt}</td><td>{att}</td></tr>')
    return ('<table><thead><tr><th>Rep</th><th>New + upsell won, 2026</th><th>Annual quota</th>'
            '<th>Attained</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>')


BODY = f'''
<main>
<h1>GTM Executive Dashboard — replica</h1>
<p class="sub">Built from live Salesforce data (as of {esc(D['asOf'])}) and plan targets from the Reporting Data Warehouse sheet.
Closed-quarter figures use Q1–Q3; Q4 is in progress.</p>

<div class="kpis">
  <div class="kpi"><span>YTD bookings (new + upsell)</span><b>{m(ytd_bookings)}</b><small>{pct(ytd_bookings, fy_plan)} of {m(fy_plan, 1)} FY plan</small></div>
  <div class="kpi"><span>YTD new business</span><b>{m(ytd_new)}</b><small>plan {m(T['annual']['new'], 1)} FY</small></div>
  <div class="kpi"><span>YTD upsell</span><b>{m(ytd_up)}</b><small>plan {m(T['annual']['upsell'], 1)} FY</small></div>
  <div class="kpi"><span>YTD churn</span><b class="neg">{m(ytd_churn)}</b><small>allowance {m(sum(tol.values()), 1)}</small></div>
  <div class="kpi"><span>Open pipeline, 2026 close</span><b>{m(open_total)}</b><small>Commit {m(open_by_fc['Commit'])}</small></div>
  <div class="kpi"><span>Simple ARR roll-forward</span><b>{m(roll_arr)}</b><small>Jan-26 opening {m(beg_arr, 1)}</small></div>
</div>

<h2>Bookings by quarter vs plan</h2>
{quarter_cards()}
<div class="legend"><i style="background:var(--new)"></i>New business<i style="background:var(--up)"></i>Upsell</div>
<div class="card" style="margin-top:12px">{bookings_table()}</div>

<h2>Churn and renewals</h2>
<div class="card">{churn_table()}
<div class="note">Total churn = Churn_Amount__c on lost renewals plus on won renewals (won renewals carry churn only in Q2). Allowance is the churn tolerance in the plan sheet, shown as a positive amount.</div></div>

<h2>Open pipeline by forecast category</h2>
<div class="card">{forecast_table()}
<div class="note">Open opportunities with a 2026 close date, Migration excluded, Deal ARR &gt; 0. The published dashboard’s $16.3M open pipeline uses a different scope (it excludes Stage 0 and renewals, and includes 2027 close dates), so the two are not comparable yet.</div></div>

<h2>Rep attainment (new + upsell won, 2026)</h2>
<div class="card">{rep_table()}
<div class="note">Attained = 2026 won ARR ÷ annual quota. Quotas are from the rep quota sheet, already in whole dollars. Adam Fox has no quota on file.</div></div>

<h2>Method and sources</h2>
<div class="card" style="font-size:13px">
<ul style="margin:0;padding-left:18px">
<li><b>Bookings and churn</b>: Salesforce Opportunity, CloseDate in 2026, Type ≠ Migration, Deal_ARR__c &gt; 0. Wins use IsWon. Renewal churn is Churn_Amount__c.</li>
<li><b>Plan</b>: quarterly and annual targets parsed from the Reporting Data Warehouse workbook (data/slow/sheet_targets.json, as of 2026-10-27 per data/slow/MANIFEST.json).</li>
<li><b>Beginning ARR</b>: Jan-26 opening ARR of {m(beg_arr, 1)} from the workbook’s ARR-by-month block.</li>
<li><b>Simple roll-forward</b> = opening ARR + YTD new + YTD upsell − YTD churn. It leaves out renewal uplift, so it does not match the published figure.</li>
</ul>
<p class="note" style="margin-top:10px">Not reproduced yet: NRR and GRR, the Summary verdict, partner channel, Demand Gen and landing pages, Sales Productivity, Pipeline Productivity, Customer Health, Top Accounts and the stage-conversion ladders. Each needs an extra query or a sheet tab that has not been pulled.</p>
</div>
</main>
'''

PAGE = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GTM Dashboard — replica</title><style>{CSS}</style></head>
<body>{BODY}</body></html>
'''

with open(OUT, 'w', encoding='utf-8') as fh:
    fh.write(PAGE)

print(f'wrote {OUT}')
print(f'YTD new {m(ytd_new)}  upsell {m(ytd_up)}  bookings {m(ytd_bookings)}  churn {m(ytd_churn)}')
print(f'closed-quarter attainment {pct(closed_actual, closed_plan)}  FY attainment {pct(ytd_bookings, fy_plan)}')
print(f'open {m(open_total)}  roll-forward {m(roll_arr)}')
