"""Builds the Pre-Audit report (Markdown + self-contained printable HTML)
from a deterministic `calculator.SimulationResult`."""

from __future__ import annotations

import html
from datetime import datetime

import calculator as calc
from calculator import fmt_minutes, fmt_num

VERDICT_COLORS = {
    calc.VERDICT_GREEN: ("#15803d", "#dcfce7"),
    calc.VERDICT_YELLOW: ("#a16207", "#fef9c3"),
    calc.VERDICT_RED: ("#b91c1c", "#fee2e2"),
}
VERDICT_EMOJI = {calc.VERDICT_GREEN: "🟢", calc.VERDICT_YELLOW: "🟡", calc.VERDICT_RED: "🔴"}


def report_sections(res: calc.SimulationResult) -> dict:
    """Structured content shared by the Markdown and HTML renderers."""
    i = res.inp
    s1 = [
        ("Verdict", f"{res.verdict} — {res.verdict_title}"),
        ("Scor potrivire", f"{res.score}/100"),
        ("Amortizare orientativă", f"{res.payback} ({i.shifts} {'schimb' if i.shifts == 1 else 'schimburi'}/zi; interval general {calc.PAYBACK_RANGE})"),
        ("Preț scenariu", calc.SCENARIO_PRICE),
        ("Livrare orientativă", f"{calc.DELIVERY_ESTIMATE} (reper PURATOS)"),
    ]
    facts = [
        "7,4 găleți/min la 13 kg (44 găleți/palet)",
        "8,6 găleți/min la 5 kg (100 găleți/palet)",
        "Țintă minimă proiect: 6 găleți/min",
        "Termen de livrare ~4 luni",
    ]
    s2 = [
        ("Sarcină totală (găleată + gripper)", f"{fmt_num(i.bucket_weight_kg)} kg + {fmt_num(i.gripper_weight_kg)} kg = {fmt_num(res.payload_total)} kg din 20,0 kg ({fmt_num(res.payload_pct, 0)}%)"),
        ("Marjă de siguranță față de 20 kg", f"{fmt_num(res.safety_margin_kg)} kg"),
        ("Reper cadență aplicabil", res.benchmark_label),
        ("Debit linie amonte", f"{fmt_num(i.line_rate_bpm, 2)} găleți/min"),
        ("Grad de încărcare vs. reper", f"{fmt_num(res.load_pct, 0)}%"),
    ]
    flow_warnings = []
    if res.bottleneck:
        flow_warnings.append("GÂTUIRE: debit > 8,6 găleți/min. Recomandare: 2 celule UR20 în paralel sau analiză flux amonte/aval.")
    elif res.above_benchmark:
        flow_warnings.append(f"Debitul depășește reperul testat de {fmt_num(res.benchmark_bpm)} găleți/min pentru această greutate — necesită test de cadență.")
    if res.payload_total > calc.UR20_MAX_PAYLOAD_KG:
        flow_warnings.append(f"SUPRASARCINĂ: {fmt_num(res.payload_total)} kg > 20 kg — configurație incompatibilă UR20.")

    side_desc = {
        "Stânga": "Stânga — robotul paletizează doar pe poziția stângă; operatorul pregătește poziția dreaptă.",
        "Dreapta": "Dreapta — robotul paletizează doar pe poziția dreaptă; operatorul pregătește poziția stângă.",
        "Dual": "Dual — robotul alternează între cele 2 poziții; paletul plin se schimbă în timp ce robotul lucrează pe celălalt.",
    }[i.side_selection]
    s3 = [
        ("Selecție preluare operator", side_desc),
        ("Configurație palet", f"{i.buckets_per_pallet} găleți / {i.layers} straturi ({fmt_num(res.buckets_per_layer, 1 if res.buckets_per_layer % 1 else 0)} găleți/strat)"),
        ("Fereastră schimb palet (timp umplere palet)", fmt_minutes(res.fill_time_min)),
        ("Interval așezare manuală separator", fmt_minutes(res.separator_time_min)),
        ("Echipament schimb paleți", i.pallet_equipment),
        ("Siguranță", "3 scanere optice de siguranță pe cele 2 poziții de paletizare"),
    ]
    return {
        "s1": s1, "facts": facts, "s2": s2, "flow_warnings": flow_warnings, "s3": s3,
        "manual": calc.MANUAL_TASKS, "out_of_scope": calc.OUT_OF_SCOPE,
        "hardware": res.hardware, "risks": res.risks, "notes": res.notes,
        "confidential": list(i.confidential_fields),
        "hub": res.hub, "actions": calc.ONSITE_ACTIONS,
        "inputs": input_summary(i),
    }


def input_summary(i: calc.SimulationInput) -> list[tuple[str, str]]:
    return [
        ("Industrie", i.industry),
        ("Greutate găleată plină", f"{fmt_num(i.bucket_weight_kg)} kg"),
        ("Greutate gripper estimată", f"{fmt_num(i.gripper_weight_kg)} kg"),
        ("Tip conținut", i.content_type),
        ("Mâner / toartă mobilă", "Da" if i.has_handle else "Nu"),
        ("Debit linie amonte", f"{fmt_num(i.line_rate_bpm, 2)} găleți/min"),
        ("Configurație palet", i.pallet_config if i.pallet_config != calc.PALLET_CUSTOM else f"Custom ({i.buckets_per_pallet} găleți, {i.layers} straturi)"),
        ("Selecție preluare", i.side_selection),
        ("Schimburi/zi", str(i.shifts)),
        ("Aer comprimat", i.air_supply),
        ("Echipament schimb paleți", i.pallet_equipment),
        ("Județ", i.county),
    ]


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------
def build_markdown(res: calc.SimulationResult) -> str:
    d = report_sections(res)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    L: list[str] = []
    L.append("# Fișă Tehnică de Pre-Fezabilitate — Pre-Audit UR20")
    L.append(f"_Generat: {now} · Demo cu date fictive · Tech-Con România_")
    L.append("")
    L.append("> ⚠️ Pre-calificare tehnică orientativă bazată pe date fictive. Nu constituie ofertă fermă.")
    L.append("")
    L.append("## Date de intrare (ipoteze introduse)")
    L += [f"- **{k}:** {v}" for k, v in d["inputs"]]
    L.append("")
    L.append(f"## 1. Verdict Semafor & Încadrare Comercială  {VERDICT_EMOJI[res.verdict]}")
    L += [f"- **{k}:** {v}" for k, v in d["s1"]]
    L.append("")
    L.append(f"**{calc.LABEL_FACT}:**")
    L += [f"- {f}" for f in d["facts"]]
    L.append("")
    L.append(f"**{calc.LABEL_ESTIMATE}:** verdictul, scorul, sarcina, gradul de încărcare, timpii operatorului și fereastra de amortizare de mai jos.")
    L.append("")
    L.append("## 2. Bilanț Mecanic & Cadență")
    L += [f"- **{k}:** {v}" for k, v in d["s2"]]
    L += [f"- ⚠️ {w}" for w in d["flow_warnings"]]
    L.append("")
    L.append("## 3. Protocol Om–Robot")
    L += [f"- **{k}:** {v}" for k, v in d["s3"]]
    L.append("- **Operații manuale (operator):** " + "; ".join(d["manual"]))
    L.append("- **În afara scopului celulei automate:** " + "; ".join(d["out_of_scope"]))
    L.append("")
    L.append("## 4. Echipare & Riscuri Specifice")
    L.append("**Echipare:**")
    L += [f"- {name} — _{status}_" for name, status in d["hardware"]]
    L.append("")
    L.append("**Riscuri detectate:**")
    if d["risks"]:
        L += [f"- **{r.title}**{' (semnalat în discuție)' if r.source == 'chat' else ''}: {r.detail}" for r in d["risks"]]
    else:
        L.append("- Niciun risc critic detectat pe baza ipotezelor introduse.")
    if d["notes"]:
        L.append("")
        L.append("**Observații:**")
        L += [f"- {n}" for n in d["notes"]]
    L.append("")
    L.append("**Confidențial / De verificat on-site:**")
    L += [f"- {c}" for c in d["confidential"]] or ["- Niciun câmp marcat."]
    L.append("")
    L.append("## 5. Alocare Hub Tech-Con & Pași Următori")
    L.append(f"- **Hub alocat:** {d['hub']} (județ {res.inp.county})")
    L += [f"{n}. {a}" for n, a in enumerate(d["actions"], 1)]
    L.append("")
    L.append("---")
    L.append("_Nu se calculează economii salariale sau ROI personalizat. Fereastra de amortizare și prețul sunt orientative._")
    return "\n".join(L)


# --------------------------------------------------------------------------
# Printable HTML
# --------------------------------------------------------------------------
def _rows(items) -> str:
    return "".join(f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>" for k, v in items)


def _bar(label: str, value: float, maximum: float, color: str, text: str) -> str:
    pct = max(0.0, min(100.0, value / maximum * 100 if maximum else 0))
    return (
        f'<div class="bar"><div class="bl">{html.escape(label)}</div>'
        f'<div class="bt"><div class="bf" style="width:{pct:.1f}%;background:{color}"></div></div>'
        f'<div class="bv">{html.escape(text)}</div></div>'
    )


def build_html(res: calc.SimulationResult) -> str:
    d = report_sections(res)
    fg, bg = VERDICT_COLORS[res.verdict]
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    esc = html.escape
    payload_color = "#b91c1c" if res.payload_total > 20 else ("#a16207" if res.safety_margin_kg < calc.LOW_MARGIN_KG else "#15803d")
    load_color = "#b91c1c" if res.bottleneck else ("#a16207" if res.above_benchmark else "#15803d")
    bars = _bar("Sarcină vs. 20 kg", res.payload_total, 20.0, payload_color, f"{fmt_num(res.payload_total)} / 20 kg") + \
        _bar(f"Încărcare vs. reper {fmt_num(res.benchmark_bpm)}", res.load_pct, 150.0, load_color, f"{fmt_num(res.load_pct, 0)}%")
    risks_html = "".join(
        f"<li><b>{esc(r.title)}</b>{' <i>(semnalat în discuție)</i>' if r.source == 'chat' else ''}: {esc(r.detail)}</li>" for r in d["risks"]
    ) or "<li>Niciun risc critic detectat pe baza ipotezelor introduse.</li>"
    notes_html = ("<p><b>Observații:</b></p><ul>" + "".join(f"<li>{esc(n)}</li>" for n in d["notes"]) + "</ul>") if d["notes"] else ""
    conf_html = "".join(f"<li>{esc(c)}</li>" for c in d["confidential"]) or "<li>Niciun câmp marcat.</li>"
    warn_html = "".join(f'<div class="warn">⚠️ {esc(w)}</div>' for w in d["flow_warnings"])
    hw_html = "".join(f"<tr><th>{esc(n)}</th><td>{esc(s)}</td></tr>" for n, s in d["hardware"])
    actions_html = "".join(f"<li>{esc(a)}</li>" for a in d["actions"])

    return f"""<!doctype html>
<html lang="ro"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pre-Audit UR20 — Fișă Tehnică</title>
<style>
  body {{ font-family: "Segoe UI", Roboto, Arial, sans-serif; color:#0f172a; margin:0; background:#f1f5f9; }}
  .page {{ max-width:860px; margin:24px auto; background:#fff; padding:28px 32px; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,.08); }}
  h1 {{ font-size:22px; margin:0 0 2px; }}
  h2 {{ font-size:15px; margin:18px 0 6px; padding-bottom:4px; border-bottom:2px solid #e2e8f0; color:#0c4a6e; }}
  .meta {{ color:#64748b; font-size:12px; margin-bottom:10px; }}
  .disc {{ background:#fff7ed; border:1px solid #fdba74; color:#9a3412; padding:6px 10px; border-radius:6px; font-size:12px; }}
  .verdict {{ display:flex; gap:14px; align-items:center; background:{bg}; border:2px solid {fg}; border-radius:10px; padding:10px 14px; margin-top:12px; }}
  .badge {{ background:{fg}; color:#fff; font-weight:800; padding:6px 12px; border-radius:6px; font-size:16px; }}
  .score {{ margin-left:auto; font-size:26px; font-weight:800; color:{fg}; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ text-align:left; padding:4px 6px; border-bottom:1px solid #f1f5f9; vertical-align:top; }}
  th {{ width:42%; color:#334155; font-weight:600; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
  .box {{ border:1px solid #e2e8f0; border-radius:8px; padding:8px 10px; font-size:12.5px; }}
  .fact {{ border-left:4px solid #0284c7; }}
  .est {{ border-left:4px solid #a16207; }}
  .box b.t {{ display:block; margin-bottom:4px; font-size:12px; }}
  ul, ol {{ margin:4px 0 4px 18px; padding:0; font-size:13px; }}
  .warn {{ background:#fef3c7; border:1px solid #f59e0b; padding:5px 8px; border-radius:6px; font-size:12.5px; margin:4px 0; }}
  .bar {{ display:grid; grid-template-columns:170px 1fr 110px; gap:8px; align-items:center; font-size:12px; margin:4px 0; }}
  .bt {{ background:#e2e8f0; border-radius:4px; height:12px; overflow:hidden; }}
  .bf {{ height:100%; }}
  .bv {{ text-align:right; font-weight:700; }}
  .foot {{ margin-top:16px; font-size:11px; color:#64748b; border-top:1px solid #e2e8f0; padding-top:6px; }}
  .print {{ text-align:right; }}
  .print button {{ font-size:13px; padding:6px 12px; cursor:pointer; }}
  @media (max-width:640px) {{ .page {{ padding:16px; margin:0; border-radius:0; }} .grid {{ grid-template-columns:1fr; }} .bar {{ grid-template-columns:1fr; }} .bv {{ text-align:left; }} }}
  @media print {{
    @page {{ size:A4; margin:12mm; }}
    body {{ background:#fff; }}
    .page {{ box-shadow:none; margin:0; padding:0; max-width:none; }}
    .print {{ display:none; }}
    h2 {{ break-after:avoid; }}
    .box, .verdict, table {{ break-inside:avoid; }}
    * {{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
  }}
</style></head>
<body><div class="page">
<div class="print"><button onclick="window.print()">🖨️ Printează / Salvează PDF</button></div>
<h1>Fișă Tehnică de Pre-Fezabilitate — Pre-Audit UR20</h1>
<div class="meta">Celulă de paletizare UR20 (referință PURATOS) · Tech-Con România · Generat: {now}</div>
<div class="disc">Demo de pre-calificare tehnică cu date fictive. Documentul nu constituie ofertă fermă și nu conține date reale.</div>

<div class="verdict"><span class="badge">{esc(res.verdict)}</span><div><b>{esc(res.verdict_title)}</b><br>
<span style="font-size:12px">Hub alocat: {esc(res.hub)} · Amortizare orientativă: {esc(res.payback)}</span></div>
<div class="score">{res.score}/100</div></div>

<h2>1. Verdict Semafor & Încadrare Comercială</h2>
<table>{_rows(d["s1"])}</table>
<div class="grid" style="margin-top:8px">
  <div class="box fact"><b class="t">📌 {esc(calc.LABEL_FACT)}</b><ul>{"".join(f"<li>{esc(f)}</li>" for f in d["facts"])}</ul></div>
  <div class="box est"><b class="t">🧮 {esc(calc.LABEL_ESTIMATE)}</b>Verdict, scor, sarcină, grad de încărcare, timpi operator și fereastra de amortizare sunt calculate determinist din datele introduse.</div>
</div>

<h2>2. Bilanț Mecanic & Cadență</h2>
{bars}
<table>{_rows(d["s2"])}</table>
{warn_html}

<h2>3. Protocol Om–Robot</h2>
<table>{_rows(d["s3"])}</table>
<p style="font-size:12.5px;margin:6px 0"><b>Operații manuale:</b> {esc("; ".join(d["manual"]))}.<br>
<b>În afara scopului celulei automate:</b> {esc("; ".join(d["out_of_scope"]))}.</p>

<h2>4. Echipare & Riscuri Specifice</h2>
<table>{hw_html}</table>
<p style="margin:8px 0 2px;font-size:13px"><b>Riscuri detectate:</b></p><ul>{risks_html}</ul>
{notes_html}
<p style="margin:8px 0 2px;font-size:13px"><b>Confidențial / De verificat on-site:</b></p><ul>{conf_html}</ul>

<h2>5. Alocare Hub Tech-Con & Pași Următori</h2>
<p style="font-size:13px;margin:4px 0"><b>Hub alocat:</b> {esc(res.hub)} (județ {esc(res.inp.county)})</p>
<ol>{actions_html}</ol>

<h2>Anexă — Date de intrare (ipoteze)</h2>
<table>{_rows(d["inputs"])}</table>

<div class="foot">Nu se calculează economii salariale sau ROI personalizat. Prețul scenariului ({esc(calc.SCENARIO_PRICE)}), termenul (~4 luni) și
amortizarea ({esc(calc.PAYBACK_RANGE)}) sunt orientative. Rezultatele PURATOS sunt rezultate de test, nu garanții universale.</div>
</div></body></html>"""
