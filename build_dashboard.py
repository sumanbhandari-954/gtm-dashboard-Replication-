#!/usr/bin/env python3
"""GTM dashboard replica: tabbed page built from Salesforce aggregates and the warehouse plan.

Inputs
  replica/data_2026.json              bookings, churn, open pipeline, rep wins (Salesforce, as of asOf)
  replica/salesforce_2026_extra.json  pipeline cohorts, renewal status, cycle time, stages, top accounts
  data/slow/sheet_targets.json        plan targets + quotas (warehouse workbook, slow tier)
  data/slow/sheet_arr_rollforward.json  Jan-26 opening ARR (warehouse workbook, slow tier)

Output
  replica/replica_dashboard.html      one self-contained page, no external requests

Run:  python3 replica/build_dashboard.py          (from the project root)
"""
import html
import json
import os
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
B = json.load(open(os.path.join(HERE, 'data_2026.json')))
X = json.load(open(os.path.join(HERE, 'salesforce_2026_extra.json')))
T = json.load(open(os.path.join(ROOT, 'data', 'slow', 'sheet_targets.json')))
RF = json.load(open(os.path.join(ROOT, 'data', 'slow', 'sheet_arr_rollforward.json')))
OUT = os.path.join(HERE, 'replica_dashboard.html')

QS = ['2026-Q1', '2026-Q2', '2026-Q3', '2026-Q4']
QL = {q: q[-2:] for q in QS}
CLOSED = ['2026-Q1', '2026-Q2', '2026-Q3']
TODAY = datetime.date.today().isoformat()
esc = lambda s: html.escape(str(s))


def m(v, d=2):
    return f'${v / 1e6:,.{d}f}M'


def k(v):
    return f'${v / 1e3:,.0f}K'


def pct(a, b):
    return f'{100 * a / b:,.0f}%' if b else '—'


# ── bookings, churn, plan ─────────────────────────────────────────────────────
won_new = {q: B['won'][q]['New Business'] for q in QS}
won_up = {q: B['won'][q]['Upsell'] for q in QS}
won_ren = {q: B['won'][q]['Renewal'] for q in QS}
plan_new = {q: T['quarterly'][q]['new'] for q in QS}
plan_up = {q: T['quarterly'][q]['upsell'] for q in QS}
plan_tot = {q: T['quarterly'][q]['total'] for q in QS}
tol = {q: -T['quarterly'][q]['churnTolerance'] for q in QS}
churn = {q: B['churn'][q]['lost'] + B['churn'][q]['wonChurn'] for q in QS}
lost_churn = {q: B['churn'][q]['lost'] for q in QS}
won_churn = {q: B['churn'][q]['wonChurn'] for q in QS}

ytd_new = sum(won_new.values())
ytd_up = sum(won_up.values())
ytd_book = ytd_new + ytd_up
ytd_churn = sum(churn.values())
fy_plan = T['annual']['total']
closed_act = sum(won_new[q] + won_up[q] for q in CLOSED)
closed_plan = sum(plan_tot[q] for q in CLOSED)

beg_arr = float(RF['monthly']['Beginning ARR']['total'].replace(',', '')) * 1000
arr_close = {}
run = beg_arr
for q in QS:
    opening = run
    run = run + won_new[q] + won_up[q] - churn[q]
    arr_close[q] = (opening, run)
roll_arr = run

fc_order = ['Commit', 'Best Case', 'Stretch', 'Omitted']
open_fc = {f: 0.0 for f in fc_order}
open_fc_type = {}
for r in B['open']:
    open_fc[r['fc']] += r['arr']
    open_fc_type[(r['fc'], r['type'])] = open_fc_type.get((r['fc'], r['type']), 0) + r['arr']
open_total = sum(open_fc.values())

# ── rep attainment ────────────────────────────────────────────────────────────
reps = {}
for r in B['ownerWon']:
    reps[r['owner']] = reps.get(r['owner'], 0.0) + r['arr']
rep_rows = sorted(((n, v, T['quotas'].get(n)) for n, v in reps.items()), key=lambda x: -x[1])

# ── pipeline cohorts (Sales_Cycle_Create_Date) ───────────────────────────────
cohort = X['cohort']['rows']


def cohort_sum(q, typ, attr=None):
    return sum(r['arr'] for r in cohort if r['q'] == q and r['type'] == typ and (attr is None or r['attr'] == attr))


def cohort_n(q, typ):
    return sum(r['n'] for r in cohort if r['q'] == q and r['type'] == typ)


# ── renewal status (open renewals) ───────────────────────────────────────────
ren_open = X['renewalStatusOpen']['rows']
overdue_arr = sum(r['arr'] for r in ren_open if r['q'] in CLOSED)
overdue_n = sum(r['n'] for r in ren_open if r['q'] in CLOSED)

# ── top accounts ─────────────────────────────────────────────────────────────
top = X['topAccounts']['rows']
top_total = sum(r['arr'] for r in top)
top5 = sum(r['arr'] for r in top[:5])

# ── HTML pieces ──────────────────────────────────────────────────────────────
def table(headers, rows, first_left=True):
    th = ''.join(f'<th>{esc(h)}</th>' for h in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows)
    return f'<div class="scroll"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def bar(parts, scale):
    segs = ''.join(f'<i style="width:{100 * v / scale:.2f}%;background:{c}"></i>' for c, v in parts if v > 0)
    return f'<div class="bar">{segs}</div>'


def quarter_cards():
    out = []
    for q in QS:
        act = won_new[q] + won_up[q]
        plan = plan_tot[q]
        scale = max(plan, act, 1)
        status = 'closed' if q in CLOSED else 'in progress'
        out.append(f'''<div class="card"><div class="lab">{QL[q]} 2026 · {status}</div>
<b class="big">{m(act)}</b> <span class="mut">of {m(plan, 1)} plan</span>
{bar([('var(--new)', won_new[q]), ('var(--up)', won_up[q])], scale)}
<div class="mut sm">{pct(act, plan)} attained · new {m(won_new[q])} · upsell {m(won_up[q])}</div></div>''')
    return '<div class="grid4">' + ''.join(out) + '</div>'


TABS = [('summary', 'Summary'), ('revenue', 'Revenue'), ('customers', 'Customers'),
        ('gtm', 'Go-to-Market'), ('reps', 'Sales Productivity'), ('notes', 'Notes')]

# Summary
summary = f'''
<div class="kpis">
 <div class="kpi"><span>YTD bookings (new + upsell)</span><b>{m(ytd_book)}</b><small>{pct(ytd_book, fy_plan)} of {m(fy_plan, 1)} FY plan</small></div>
 <div class="kpi"><span>YTD new business</span><b>{m(ytd_new)}</b><small>plan {m(T['annual']['new'], 1)}</small></div>
 <div class="kpi"><span>YTD upsell</span><b>{m(ytd_up)}</b><small>plan {m(T['annual']['upsell'], 1)}</small></div>
 <div class="kpi"><span>YTD churn</span><b class="neg">{m(ytd_churn)}</b><small>allowance {m(sum(tol.values()), 1)}</small></div>
 <div class="kpi"><span>Simple ARR roll-forward</span><b>{m(roll_arr)}</b><small>opening {m(beg_arr, 1)}</small></div>
 <div class="kpi"><span>Open pipeline, 2026 close</span><b>{m(open_total)}</b><small>Commit {m(open_fc['Commit'])}</small></div>
</div>
<h2>Bookings by quarter vs plan</h2>
{quarter_cards()}
<div class="legend"><i style="background:var(--new)"></i>New business<i style="background:var(--up)"></i>Upsell</div>
<h2>Quarterly plan vs actual</h2>
{table(['Quarter', 'New plan', 'New won', 'Upsell plan', 'Upsell won', 'Total plan', 'Total won', 'Attained'],
  [[QL[q], k(plan_new[q]), k(won_new[q]), k(plan_up[q]), k(won_up[q]), k(plan_tot[q]), k(won_new[q] + won_up[q]), pct(won_new[q] + won_up[q], plan_tot[q])] for q in QS]
  + [['<b>FY</b>', k(T['annual']['new']), k(ytd_new), k(T['annual']['upsell']), k(ytd_up), k(fy_plan), k(ytd_book), pct(ytd_book, fy_plan)]])}
<p class="note">Closed quarters are Q1–Q3. Q4 is in progress on the as-of date. Plan is the company plan from the warehouse workbook.</p>
'''

# Revenue
arr_rows = []
for q in QS:
    o, c = arr_close[q]
    arr_rows.append([QL[q], m(o), '+' + k(won_new[q]), '+' + k(won_up[q]), f'<span class="neg">−{k(churn[q])}</span>', m(c)])
revenue = f'''
<h2>ARR roll-forward (simple)</h2>
{table(['Quarter', 'Opening ARR', 'New won', 'Upsell won', 'Churn', 'Closing ARR'], arr_rows)}
<p class="note">Opening ARR is Jan-26 from the workbook. Each quarter adds won new and upsell and subtracts churn. Renewal uplift is not included, so this differs from the published figure.</p>
<h2>Renewals won (ARR) by quarter</h2>
{table(['Quarter', 'Renewals won', 'Lost-renewal churn', 'Churn on won renewals', 'Total churn', 'Planned allowance', 'vs allowance'],
  [[QL[q], k(won_ren[q]), k(lost_churn[q]), k(won_churn[q]), k(churn[q]), k(tol[q]),
    f'<span class="{"neg" if churn[q] > tol[q] else "pos"}">{"over" if churn[q] > tol[q] else "within"}</span>'] for q in QS])}
<h2>Open pipeline by forecast category (2026 close)</h2>
{table(['Forecast', 'New business', 'Upsell', 'Renewal', 'Total'],
  [[f, k(open_fc_type.get((f, 'New Business'), 0)), k(open_fc_type.get((f, 'Upsell'), 0)),
    k(open_fc_type.get((f, 'Renewal'), 0)), m(open_fc[f])] for f in fc_order]
  + [['<b>Total</b>', '', '', '', f'<b>{m(open_total)}</b>']])}
<p class="note">Open opportunities with a 2026 close date, Migration excluded, Deal ARR &gt; 0. Stage 0 and 2027 closes are not included.</p>
'''

# Customers
ren_rows = []
for r in ren_open:
    pass
ren_by_q = {}
for r in ren_open:
    ren_by_q.setdefault(r['q'], []).append(r)
ren_tbl_rows = []
for q in QS:
    items = {r['status']: r for r in ren_by_q.get(q, [])}
    def cell(s):
        r = items.get(s)
        return f'{k(r["arr"])} <span class="mut sm">({r["n"]})</span>' if r else '—'
    flag = '<span class="neg">past close date</span>' if q in CLOSED else 'current'
    ren_tbl_rows.append([QL[q], cell('Green'), cell('Yellow'), cell('Red'), cell('Unset'), flag])
top_rows = []
for i, r in enumerate(top, 1):
    top_rows.append([str(i), esc(r['name']), esc(r['industry']), k(r['arr']), pct(r['arr'], top_total)])
customers = f'''
<div class="kpis">
 <div class="kpi"><span>Open renewals, past close date</span><b class="neg">{m(overdue_arr)}</b><small>{overdue_n} opportunities still open after Q1–Q3</small></div>
 <div class="kpi"><span>Top 5 accounts share</span><b>{pct(top5, top_total)}</b><small>of the top 25 listed ARR</small></div>
</div>
<h2>Open renewals by close quarter and status</h2>
{table(['Quarter', 'Green', 'Yellow', 'Red', 'Unset', 'Status'], ren_tbl_rows)}
<p class="note">Status is Overall_Renewal_Status__c. Open renewals with close dates already past need a close or a new date. They are the main data-quality issue in this pull.</p>
<h2>Top 25 accounts by ARR</h2>
{table(['#', 'Account', 'Industry', 'Account ARR', 'Share of top 25'], top_rows)}
'''

# Go-to-Market
cohort_rows = []
for q in QS:
    nb_tot = cohort_sum(q, 'New Business')
    cohort_rows.append([QL[q], cohort_n(q, 'New Business'), k(nb_tot),
                        k(cohort_sum(q, 'New Business', 'GTM')), k(cohort_sum(q, 'New Business', 'Partner')),
                        k(cohort_sum(q, 'New Business', 'Sales')),
                        cohort_n(q, 'Upsell'), k(cohort_sum(q, 'Upsell'))])
cyc_rows = [[QL[r['q']], r['type'], r['n'], f'{r["avgDays"]:.0f}'] for r in X['cycle']['rows']]
cyc_rows.sort(key=lambda r: (r[1], r[0]))
stage_rows = []
stage_total = sum(s['arr'] for s in X['openStages2026']['rows'])
for s in X['openStages2026']['rows']:
    stage_rows.append([esc(s['stage']), s['n'], k(s['arr']), pct(s['arr'], stage_total)])
gtm = f'''
<h2>Pipeline generated by cohort (Sales Cycle Create Date)</h2>
{table(['Quarter', 'New business opps', 'New business ARR', 'GTM-sourced', 'Partner-sourced', 'Sales-sourced', 'Upsell opps', 'Upsell ARR'], cohort_rows)}
<p class="note">Cohort date, not close date. New business is the primary lens; upsell is shown separately. A null create date means never qualified, so it is not pipeline.</p>
<h2>Open pipeline by stage (2026 close)</h2>
{table(['Stage', 'Opps', 'ARR', 'Share'], stage_rows)}
<h2>Sales cycle on won deals</h2>
{table(['Quarter', 'Type', 'Won deals', 'Avg cycle (days)'], cyc_rows)}
<p class="note">Average of Sales_Cycle_Days__c. Q4 upsell cycle is short and not yet meaningful.</p>
'''

# Sales productivity
rep_tbl = []
for n, booked, quota in rep_rows:
    rep_tbl.append([esc(n), k(booked), k(quota) if quota else '<span class="mut">no quota on file</span>',
                    pct(booked, quota) if quota else '—'])
reps_html = f'''
<h2>Rep attainment: new + upsell won, 2026</h2>
{table(['Rep', 'New + upsell won', 'Annual quota', 'Attained'], rep_tbl)}
<p class="note">Attained = 2026 won ARR ÷ annual quota. Quotas are from the rep quota sheet. Totals are closed and open-quarter wins to date.</p>
'''

# Notes
notes = f'''
<h2>Sources and method</h2>
<div class="card sm">
<ul>
<li><b>Bookings, churn, open pipeline, reps, cohorts, renewals, cycle, stages, top accounts</b>: live Salesforce aggregates as of {esc(B['asOf'])}. Scope: Type ≠ Migration, Deal_ARR__c &gt; 0; wins use IsWon; churn is Churn_Amount__c.</li>
<li><b>Plan and quotas</b>: the Reporting Data Warehouse workbook (committed slow tier, as of 2026-10-27).</li>
<li><b>Opening ARR</b>: Jan-26 from the workbook’s ARR-by-month block, {m(beg_arr, 1)}.</li>
</ul>
<h2>Not reproduced yet</h2>
<p class="sm">NRR and GRR (need beginning-of-period ARR by customer), partner channel and partner scorecard (sheet tab), Demand Gen and landing pages (outbound sheet and HubSpot), Pipeline Productivity (per-rep activity), and Customer Health (CS stage).</p>
</div>
'''

PANES = {'summary': summary, 'revenue': revenue, 'customers': customers, 'gtm': gtm, 'reps': reps_html, 'notes': notes}
NAV = ''.join(f'<button class="tab{" on" if i == 0 else ""}" data-t="{t}">{esc(lbl)}</button>' for i, (t, lbl) in enumerate(TABS))
PANE_HTML = ''.join(f'<section class="pane{" on" if i == 0 else ""}" id="p-{t}">{PANES[t]}</section>' for i, (t, _) in enumerate(TABS))

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#14181f;--mut:#6b7280;--line:#e5e7eb;--new:#1f4e9c;--up:#2e9c86;--warn:#b42318;--ok:#067647}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#0f1319;--card:#171c25;--ink:#e8ebf1;--mut:#9aa3b2;--line:#262d39;--new:#7aa7ff;--up:#4fd1b5;--warn:#ff8a80;--ok:#6ee7a8}}
:root[data-theme="dark"]{--bg:#0f1319;--card:#171c25;--ink:#e8ebf1;--mut:#9aa3b2;--line:#262d39;--new:#7aa7ff;--up:#4fd1b5;--warn:#ff8a80;--ok:#6ee7a8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
header{padding:20px 16px 0;max-width:1140px;margin:0 auto}h1{font-size:22px;margin:0 0 2px}
.sub{color:var(--mut);margin:0 0 14px}
nav{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);z-index:5}
nav .in{max-width:1140px;margin:0 auto;padding:0 16px;display:flex;gap:4px;overflow-x:auto}
.tab{appearance:none;background:none;border:0;border-bottom:2px solid transparent;color:var(--mut);padding:12px 10px;font:inherit;cursor:pointer;white-space:nowrap}
.tab.on{color:var(--ink);border-bottom-color:var(--new);font-weight:600}
main{max-width:1140px;margin:0 auto;padding:8px 16px 60px}
.pane{display:none}.pane.on{display:block}
h2{font-size:15px;margin:26px 0 10px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-top:10px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}@media (max-width:760px){.grid4{grid-template-columns:1fr 1fr}}
.kpi,.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.kpi span,.lab{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.04em;display:block}
.kpi b{display:block;font-size:22px;margin-top:4px}.kpi small{color:var(--mut)}
.big{font-size:20px}.mut{color:var(--mut)}.sm{font-size:12px}
.scroll{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{color:var(--mut);font-weight:600;font-size:12px}
tr:last-child td{border-bottom:0}
.bar{height:8px;border-radius:4px;background:var(--line);overflow:hidden;display:flex;margin:8px 0 6px}.bar i{display:block;height:100%}
.legend{color:var(--mut);font-size:12px;margin:8px 0 0}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px 0 12px;vertical-align:-1px}
.note{color:var(--mut);font-size:12px;margin:8px 0 0}.neg{color:var(--warn)}.pos{color:var(--ok)}
.card ul{margin:0;padding-left:18px}
"""

JS = """
document.querySelectorAll('.tab').forEach(function(b){b.addEventListener('click',function(){
 document.querySelectorAll('.tab').forEach(function(x){x.classList.toggle('on',x===b)});
 document.querySelectorAll('.pane').forEach(function(p){p.classList.toggle('on',p.id==='p-'+b.dataset.t)});
 window.scrollTo(0,0);
})});
"""

PAGE = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GTM Dashboard — replica</title><style>{CSS}</style></head>
<body>
<header><h1>GTM Executive Dashboard — replica</h1>
<p class="sub">Salesforce as of {esc(B['asOf'])} · plan from the Reporting Data Warehouse sheet · page built {TODAY}</p></header>
<nav><div class="in">{NAV}</div></nav>
<main>{PANE_HTML}</main>
<script>{JS}</script>
</body></html>
'''

with open(OUT, 'w', encoding='utf-8') as fh:
    fh.write(PAGE)

print(f'wrote {OUT}')
print(f'bookings {m(ytd_book)}  churn {m(ytd_churn)}  roll-forward {m(roll_arr)}  open {m(open_total)}')
print(f'closed-quarter attainment {pct(closed_act, closed_plan)}  overdue renewals {m(overdue_arr)} ({overdue_n})')
