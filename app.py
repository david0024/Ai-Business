"""Tech-Con UR20 Palletizing Cell — Pre-Qualification & Interactive Simulator.

Run locally:  streamlit run app.py
All user-facing text is Romanian; all calculations live in calculator.py.
"""

from __future__ import annotations

import json
import os
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import ai_consultant
import calculator as calc
import database
import report_builder
import robot_animation

st.set_page_config(
    page_title="Pre-Audit UR20 — Tech-Con",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="auto",
)

# ==========================================================================
# 1. SESSION STATE — defaults + pending updates applied BEFORE any widget
# ==========================================================================
DEFAULTS = {
    "f_industry": calc.INDUSTRY_FOOD,
    "f_bucket": 13.0,
    "f_gripper": calc.DEFAULT_GRIPPER_KG,
    "f_content": "Pastă-vâscos",
    "f_handle": "Da",
    "f_rate": 6.5,
    "f_pallet": calc.PALLET_PRESET_13,
    "f_custom_n": 60,
    "f_custom_layers": 4,
    "f_side": "Dual",
    "f_shifts": 2,
    "f_air": "Da",
    "f_equipment": "Transpalet",
    "f_county": "Ilfov",
    "f_confidential": [],
    "f_risks": [],
    "f_new_risk": "",
}

PRESETS = {
    "Preset 1: Caz Valid (Lactate 13 kg)": {
        "f_industry": calc.INDUSTRY_FOOD, "f_bucket": 13.0, "f_gripper": 5.0, "f_content": "Pastă-vâscos",
        "f_handle": "Da", "f_rate": 6.5, "f_pallet": calc.PALLET_PRESET_13, "f_side": "Dual", "f_shifts": 2,
        "f_air": "Da", "f_equipment": "Transpalet", "f_county": "Ilfov", "f_confidential": [], "f_risks": [],
    },
    "Preset 2: Date Confidențiale / De Verificat": {
        "f_industry": calc.INDUSTRY_NONFOOD, "f_bucket": 10.0, "f_gripper": 5.0, "f_content": "Lichid",
        "f_handle": "Da", "f_rate": 7.2, "f_pallet": calc.PALLET_CUSTOM, "f_custom_n": 60, "f_custom_layers": 4,
        "f_side": "Stânga", "f_shifts": 2, "f_air": "Nu știu", "f_equipment": "Liză", "f_county": "Cluj",
        "f_confidential": ["Nume companie", "Debit exact linie de vârf"], "f_risks": [],
    },
    "Preset 3: Eroare / Suprasarcină (>20 kg)": {
        "f_industry": calc.INDUSTRY_FOOD, "f_bucket": 18.5, "f_gripper": 5.0, "f_content": "Pastă-vâscos",
        "f_handle": "Da", "f_rate": 9.2, "f_pallet": calc.PALLET_PRESET_13, "f_side": "Dreapta", "f_shifts": 3,
        "f_air": "Nu", "f_equipment": "Stivuitor", "f_county": "Iași", "f_confidential": [], "f_risks": [],
    },
    "Preset 4: Date lipsă sau greșite": {
        "f_industry": calc.INDUSTRY_FOOD, "f_bucket": 0.0, "f_gripper": 5.0, "f_content": "Pastă-vâscos",
        "f_handle": "Da", "f_rate": -3.0, "f_pallet": calc.PALLET_CUSTOM, "f_custom_n": 0, "f_custom_layers": 4,
        "f_side": "Dual", "f_shifts": 2, "f_air": "Da", "f_equipment": "Transpalet", "f_county": "Timiș",
        "f_confidential": [], "f_risks": [],
    },
}

# Chat form_updates key -> widget key (+ value transform)
CHAT_TO_WIDGET = {
    "industry": ("f_industry", lambda v: v),
    "bucket_weight_kg": ("f_bucket", float),
    "gripper_weight_kg": ("f_gripper", float),
    "content_type": ("f_content", lambda v: v),
    "has_handle": ("f_handle", lambda v: "Da" if v else "Nu"),
    "line_rate_bpm": ("f_rate", float),
    "shifts": ("f_shifts", int),
    "side_selection": ("f_side", lambda v: v),
    "region": ("f_county", lambda v: v),
    "air_supply": ("f_air", lambda v: v),
    "pallet_equipment": ("f_equipment", lambda v: v),
}

ss = st.session_state
for key, value in DEFAULTS.items():
    if key not in ss:
        ss[key] = list(value) if isinstance(value, list) else value
ss.setdefault("risk_options", [])
ss.setdefault("chat_history", [])
ss.setdefault("chat_known", set())
ss.setdefault("flash", [])


def apply_pending_updates() -> None:
    """Apply preset / chatbot updates into widget keys before widgets exist."""
    pending = ss.pop("_pending", None)
    if not pending:
        return
    for key, value in pending.items():
        if key == "f_risks":
            for r in value:
                if r not in ss.risk_options:
                    ss.risk_options.append(r)
        ss[key] = value


apply_pending_updates()


def queue_updates(updates: dict, flash: str | None = None, flash_type: str = "success") -> None:
    ss["_pending"] = updates
    if flash:
        ss.flash.append((flash_type, flash))
    st.rerun()


def current_input() -> calc.SimulationInput:
    return calc.SimulationInput(
        industry=ss.f_industry,
        bucket_weight_kg=float(ss.f_bucket or 0),
        gripper_weight_kg=float(ss.f_gripper or 0),
        content_type=ss.f_content,
        has_handle=ss.f_handle == "Da",
        line_rate_bpm=float(ss.f_rate or 0),
        pallet_config=ss.f_pallet,
        custom_buckets_per_pallet=int(ss.f_custom_n or 0),
        custom_layers=int(ss.f_custom_layers or 0),
        side_selection=ss.f_side,
        shifts=int(ss.f_shifts),
        air_supply=ss.f_air,
        pallet_equipment=ss.f_equipment,
        county=ss.f_county,
        confidential_fields=list(ss.f_confidential),
        custom_risks=list(ss.f_risks),
    )


def get_secret(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    try:
        return st.secrets.get(name)  # type: ignore[attr-defined]
    except Exception:
        return None


database.init_db()

# ==========================================================================
# 2. STYLES (mobile-first)
# ==========================================================================
st.markdown(
    """
<style>
.block-container { padding-top: 1.2rem; padding-bottom: 3rem; }
.disclaimer { background:#fff7ed; border:1px solid #fb923c; border-left:6px solid #ea580c; color:#7c2d12;
  padding:10px 14px; border-radius:8px; font-size:0.92rem; margin-bottom:0.6rem; }
.cards { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:10px; margin:0.4rem 0 0.8rem; }
.card { border:1px solid rgba(148,163,184,.45); border-radius:10px; padding:10px 12px; font-size:0.86rem; line-height:1.4;
  background:rgba(148,163,184,.07); }
.card h4 { margin:0 0 4px; font-size:0.95rem; padding:0; }
.card .tag { display:inline-block; font-size:0.72rem; border-radius:999px; padding:1px 8px; margin-bottom:4px; }
.tag.fact { background:#e0f2fe; color:#075985; } .tag.est { background:#fef3c7; color:#92400e; } .tag.scope { background:#f1f5f9; color:#334155; }
.verdict { border-radius:12px; padding:12px 16px; display:flex; flex-wrap:wrap; gap:10px; align-items:center; }
.verdict .badge { color:#fff; font-weight:800; padding:6px 12px; border-radius:8px; font-size:1.05rem; }
.verdict .score { margin-left:auto; font-size:1.9rem; font-weight:800; }
.label-fact { border-left:4px solid #0284c7; padding:6px 10px; background:rgba(2,132,199,.08); border-radius:6px; font-size:0.86rem; margin:4px 0; }
.label-est { border-left:4px solid #b45309; padding:6px 10px; background:rgba(180,83,9,.08); border-radius:6px; font-size:0.86rem; margin:4px 0; }
@media (max-width: 900px) { .cards { grid-template-columns:repeat(2, minmax(0,1fr)); } }
@media (max-width: 520px) { .cards { grid-template-columns:1fr; } .verdict .score { margin-left:0; } h1 { font-size:1.65rem !important; } }
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================================================
# 3. SIDEBAR — AI consultant (synchronized with the form)
# ==========================================================================
API_KEY = get_secret("OPENROUTER_API_KEY")
MODEL = get_secret("OPENROUTER_MODEL") or ai_consultant.DEFAULT_MODEL

EXAMPLE_PROMPTS = [
    "Facem 10 tone de iaurt pe schimb de 8 ore, găleți de 10 kg cu toartă, lângă Cluj",
    "Cât costă celula și în cât timp se amortizează?",
    "Avem condens și spațiu strâmt, găleți ovale; debitul exact e confidențial",
    "De ce nu sunt incluse MiR, înfolierea și expedierea?",
]


def handle_chat(text: str) -> None:
    text = (text or "").strip()
    if not text:
        return
    inp = current_input()
    current = {
        "industry": inp.industry, "bucket_weight_kg": inp.bucket_weight_kg, "gripper_weight_kg": inp.gripper_weight_kg,
        "content_type": inp.content_type, "has_handle": inp.has_handle, "line_rate_bpm": inp.line_rate_bpm,
        "shifts": inp.shifts, "side_selection": inp.side_selection, "region": inp.county,
        "air_supply": inp.air_supply, "pallet_equipment": inp.pallet_equipment,
    }
    result = ai_consultant.process_message(
        text, current, known_fields=ss.chat_known, history=ss.chat_history, api_key=API_KEY, model=MODEL
    )
    ss.chat_known = result["known_fields"]
    pending: dict = {}
    for key, value in result["form_updates"].items():
        if key in CHAT_TO_WIDGET:
            wkey, conv = CHAT_TO_WIDGET[key]
            pending[wkey] = conv(value)
    if result["custom_risks"]:
        pending["f_risks"] = list(dict.fromkeys(list(ss.f_risks) + result["custom_risks"]))
    if result["confidential_fields"]:
        pending["f_confidential"] = list(dict.fromkeys(list(ss.f_confidential) + result["confidential_fields"]))
    meta = []
    if result["calc_note"]:
        meta.append(f"🧮 Calcul determinist (Python): {result['calc_note']}")
    if result["source"] == "fallback" and API_KEY and result.get("error"):
        meta.append(f"ℹ️ Consultant LLM indisponibil ({result['error']}) — răspuns generat de parserul local.")
    ss.chat_history.append({"role": "user", "content": text})
    ss.chat_history.append({
        "role": "assistant", "content": result["reply"], "meta": meta,
        "ready": result["ready_for_report"], "updated": bool(pending),
    })
    queue_updates(pending)


with st.sidebar:
    st.header("💬 Consultant Tehnic AI")
    mode = f"LLM OpenRouter ({MODEL})" if API_KEY else "parser local determinist (fără cheie API)"
    st.caption(f"Mod: **{mode}**. Toate calculele sunt făcute în Python, nu de AI. Folosiți doar date fictive.")

    chat_box = st.container(height=380, border=True)
    with chat_box:
        if not ss.chat_history:
            st.markdown(
                "Descrieți linia de producție (fictivă) și completez automat formularul, sau întrebați-mă despre "
                "preț, amortizare, siguranță, selecția Stânga/Dreapta ori ce **nu** este inclus."
            )
        for msg in ss.chat_history:
            with st.chat_message(msg["role"], avatar="🧑‍🏭" if msg["role"] == "user" else "🤖"):
                st.markdown(msg["content"])
                for m in msg.get("meta", []):
                    st.caption(m)
                if msg["role"] == "assistant" and msg.get("updated"):
                    st.caption("✅ Formularul, animația și raportul au fost actualizate.")

    with st.form("chat_form", clear_on_submit=True):
        chat_text = st.text_area(
            "Mesaj", placeholder="Ex: găleți de 5 kg fără mâner, 450 găleți pe oră, 3 schimburi, lângă Iași",
            height=90, label_visibility="collapsed",
        )
        sent = st.form_submit_button("Trimite ➤", width="stretch", type="primary")
    if sent:
        if chat_text.strip():
            handle_chat(chat_text)
        else:
            st.warning("Scrieți un mesaj înainte de trimitere.")

    st.caption("Exemple rapide:")
    for i, example in enumerate(EXAMPLE_PROMPTS):
        if st.button(example, key=f"ex_{i}", width="stretch"):
            handle_chat(example)
    if ss.chat_history and st.button("🗑️ Golește conversația", width="stretch"):
        ss.chat_history = []
        ss.chat_known = set()
        st.rerun()

# ==========================================================================
# 4. HEADER, DISCLAIMER, SPEC CARDS
# ==========================================================================
st.markdown(
    '<div class="disclaimer">⚠️ <b>Demo de pre-calificare tehnică — doar date fictive.</b> '
    "Nu introduceți date personale reale (nume, e-mail, telefon) și nici informații confidențiale ale companiei. "
    "Folosiți exclusiv date de test fictive.</div>",
    unsafe_allow_html=True,
)
st.title("🤖 Celula de paletizare UR20 — Pre-Audit & Simulator")
st.caption("Referință: celulă implementată de Tech-Con România la PURATOS · Consultantul AI este în bara laterală (☰ / » pe mobil).")

st.markdown(
    """
<div class="cards">
 <div class="card"><h4>🔄 Flux Proces</h4>
  Transportor alimentare → Cameră vision 2D SICK (detectare orientare mâner) → Braț UR20 + gripper pneumatic personalizat → 2 poziții de paletizare pe europaleți.</div>
 <div class="card"><h4>📊 Repere Testate PURATOS</h4><span class="tag fact">rezultate de test, nu garanții universale</span><br>
  <b>7,4 găleți/min</b> pentru 13 kg (44 găleți/palet) și <b>8,6 găleți/min</b> pentru 5 kg (100 găleți/palet), peste ținta minimă de 6 găleți/min.</div>
 <div class="card"><h4>🛡️ Operare & Siguranță</h4>
  3 scanere optice de siguranță pe cele 2 poziții; operatorul selectează partea activă (Stânga/Dreapta), schimbă paleții manual și așază manual separatoarele.<br>
  <span class="tag scope">În afara scopului: transport autonom MiR, înfoliere, expediere</span></div>
 <div class="card"><h4>📦 Livrare & Amortizare</h4><span class="tag est">orientativ</span><br>
  Termen <b>~4 luni</b> (reper PURATOS); amortizare orientativă <b>18–40 luni</b>; preț scenariu <b>130.000 EUR (fără TVA)</b>.</div>
</div>
""",
    unsafe_allow_html=True,
)

# Flash messages from presets / chat / CRM actions
for kind, text in ss.flash:
    getattr(st, kind)(text)
ss.flash = []

# Compute everything up-front from session state (widgets below share the same keys)
inp = current_input()
errors = calc.validate(inp)
result = calc.simulate(inp) if not errors else None

# ==========================================================================
# 5. ANIMATION
# ==========================================================================
st.subheader("🎥 Animație interactivă celulă UR20")
payload_preview = inp.bucket_weight_kg + inp.gripper_weight_kg
_embed_html = getattr(st, "iframe", None) or components.html  # st.iframe on new Streamlit, fallback otherwise
_embed_html(
    robot_animation.build_animation_html(
        line_rate_bpm=inp.line_rate_bpm,
        bucket_weight_kg=inp.bucket_weight_kg,
        gripper_weight_kg=inp.gripper_weight_kg,
        has_handle=inp.has_handle,
        side_selection=inp.side_selection,
        buckets_per_pallet=inp.buckets_per_pallet if inp.buckets_per_pallet > 0 else 1,
        layers=inp.layers if inp.layers > 0 else 1,
        benchmark_bpm=calc.benchmark_for_weight(inp.bucket_weight_kg),
        payload_total=payload_preview,
        valid=not errors,
    ),
    height=robot_animation.ANIMATION_HEIGHT,
)
st.caption(
    "Vedere de sus, simulare accelerată. Animația se sincronizează cu formularul și consultantul AI; "
    "butoanele din animație (Pauză, previzualizare Stânga/Dreapta/Dual) nu modifică formularul."
)

# ==========================================================================
# 6. TABS — Simulator & report | CRM
# ==========================================================================
tab_sim, tab_crm = st.tabs(["🧮 Simulator & Fișă Pre-Audit", "📇 Cereri Relevante Tech-Con (Demo CRM)"])

with tab_sim:
    st.markdown("#### ⚡ Preseturi rapide")
    pcols = st.columns(2) + st.columns(2)
    for col, (name, values) in zip(pcols, PRESETS.items()):
        if col.button(name, width="stretch"):
            queue_updates(dict(values), f"✅ {name} aplicat — formularul, animația și raportul au fost actualizate.")

    st.markdown("#### 📝 Formular tehnic (10 parametri)")
    with st.container(border=True):
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.radio("1. Industrie", calc.INDUSTRIES, key="f_industry", horizontal=True,
                     help="Industria non-alimentară necesită o validare tehnică separată.")
            w1, w2 = st.columns(2)
            w1.number_input("2. Greutate găleată plină (kg)", key="f_bucket", step=0.5, format="%.1f")
            w2.number_input("Greutate gripper pneumatic estimată (kg)", key="f_gripper", step=0.1, format="%.1f")
            st.radio("3. Tip conținut", calc.CONTENT_TYPES, key="f_content", horizontal=True)
            st.radio("4. Mâner / toartă mobilă?", calc.YES_NO, key="f_handle", horizontal=True,
                     help="«Da» activează camera vision 2D SICK în lista de echipamente și în animație.")
            st.number_input("5. Debit linie amonte (găleți/minut)", key="f_rate", step=0.1, format="%.2f")
            st.selectbox("6. Configurație palet", calc.PALLET_CONFIGS, key="f_pallet")
            if ss.f_pallet == calc.PALLET_CUSTOM:
                k1, k2 = st.columns(2)
                k1.number_input("Nr. găleți pe palet", key="f_custom_n", step=1)
                k2.number_input("Nr. straturi", key="f_custom_layers", step=1)
        with c2:
            st.radio("7. Selecție preluare operator", calc.SIDES, key="f_side", horizontal=True,
                     help="Selectabil din panoul operatorului.")
            st.radio("8. Număr schimburi/zi", calc.SHIFTS, key="f_shifts", horizontal=True)
            st.markdown("**9. Utilități & Acces**")
            st.radio("Aer comprimat disponibil", calc.AIR_OPTIONS, key="f_air", horizontal=True)
            st.radio("Echipament schimb paleți", calc.PALLET_EQUIPMENT, key="f_equipment", horizontal=True)
            st.selectbox(
                "10. Regiune / Județ", calc.COUNTIES, key="f_county",
                format_func=lambda c: f"{c} → hub {calc.hub_for_county(c)}",
            )
            conf_options = list(dict.fromkeys(calc.CONFIDENTIAL_FIELD_OPTIONS + list(ss.f_confidential)))
            st.multiselect("Câmpuri «Confidențial / De verificat on-site»", conf_options, key="f_confidential",
                           help="Nu blochează raportul; câmpurile apar într-o secțiune dedicată și duc la verdict Galben.")
            risk_options = list(dict.fromkeys(ss.risk_options + list(ss.f_risks)))
            st.multiselect("Riscuri specifice de șantier (din chat sau adăugate manual)", risk_options, key="f_risks",
                           placeholder="Niciun risc specific adăugat")
            r1, r2 = st.columns([3, 1], vertical_alignment="bottom")
            r1.text_input("Adaugă risc", key="f_new_risk", placeholder="Ex: temperatură scăzută în hală")
            if r2.button("➕ Adaugă", width="stretch"):
                new_risk = ss.f_new_risk.strip()
                if new_risk:
                    queue_updates({"f_risks": list(dict.fromkeys(list(ss.f_risks) + [new_risk])), "f_new_risk": ""},
                                  "Risc adăugat în raport.")
                else:
                    st.warning("Scrieți descrierea riscului.")

    # ----------------------------------------------------------------------
    # Report
    # ----------------------------------------------------------------------
    st.markdown("### 📄 Fișă Tehnică de Pre-Fezabilitate — Pre-Audit UR20")
    if errors:
        st.error(
            "**Raportul nu poate fi generat — date tehnice invalide sau lipsă:**\n\n"
            + "\n".join(f"- {e}" for e in errors)
        )
    else:
        res = result
        fg, bg = report_builder.VERDICT_COLORS[res.verdict]
        st.markdown(
            f'<div class="verdict" style="background:{bg};border:2px solid {fg};color:#0f172a">'
            f'<span class="badge" style="background:{fg}">{report_builder.VERDICT_EMOJI[res.verdict]} {res.verdict}</span>'
            f"<div><b>{res.verdict_title}</b><br><span style='font-size:.85rem'>Hub alocat: {res.hub} · "
            f"Amortizare orientativă: {res.payback}</span></div>"
            f'<span class="score" style="color:{fg}">{res.score}/100</span></div>',
            unsafe_allow_html=True,
        )

        # Section 1
        with st.container(border=True):
            st.markdown("##### 1. Verdict Semafor & Încadrare Comercială")
            m = st.columns(4)
            m[0].metric("Scor potrivire", f"{res.score}/100")
            m[1].metric("Amortizare orientativă", res.payback, help=f"{inp.shifts} schimburi/zi; interval general 18–40 luni")
            m[2].metric("Preț scenariu", "130.000 EUR", help="fără TVA")
            m[3].metric("Livrare orientativă", "~4 luni", help="reper PURATOS")
            f1, f2 = st.columns(2)
            f1.markdown(
                f'<div class="label-fact">📌 <b>{calc.LABEL_FACT}</b><br>7,4 găleți/min la 13 kg (44/palet) · '
                "8,6 găleți/min la 5 kg (100/palet) · țintă minimă 6 găleți/min · livrare ~4 luni</div>",
                unsafe_allow_html=True,
            )
            f2.markdown(
                f'<div class="label-est">🧮 <b>{calc.LABEL_ESTIMATE}</b><br>Verdict, scor, sarcină, grad de încărcare, '
                "timpi operator și fereastra de amortizare — calculate determinist în Python.</div>",
                unsafe_allow_html=True,
            )
            st.caption("Nu se calculează economii salariale sau ROI personalizat.")

        # Section 2
        with st.container(border=True):
            st.markdown("##### 2. Bilanț Mecanic & Cadență")
            m = st.columns(4)
            m[0].metric("Sarcină totală", f"{calc.fmt_num(res.payload_total)} kg",
                        help=f"{calc.fmt_num(inp.bucket_weight_kg)} kg găleată + {calc.fmt_num(inp.gripper_weight_kg)} kg gripper")
            m[1].metric("Marjă vs. 20 kg", f"{calc.fmt_num(res.safety_margin_kg)} kg")
            m[2].metric("Reper PURATOS", f"{calc.fmt_num(res.benchmark_bpm)} găl./min")
            m[3].metric("Grad încărcare", f"{calc.fmt_num(res.load_pct, 0)}%")

            def bullet(value, maximum, threshold, color, suffix, title):
                fig = go.Figure(go.Indicator(
                    mode="number+gauge", value=value,
                    number={"suffix": suffix, "valueformat": ".1f", "font": {"size": 20}},
                    gauge={
                        "shape": "bullet", "axis": {"range": [0, maximum]},
                        "bar": {"color": color, "thickness": 0.55},
                        "threshold": {"line": {"color": "#0f172a", "width": 3}, "thickness": 0.9, "value": threshold},
                        "bgcolor": "rgba(148,163,184,0.18)", "borderwidth": 0,
                    },
                    domain={"x": [0.0, 0.82], "y": [0, 1]},
                ))
                fig.update_layout(height=78, margin=dict(l=10, r=10, t=6, b=22), paper_bgcolor="rgba(0,0,0,0)", separators=",.",
                                  font=dict(size=11))
                st.caption(title)
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            payload_color = "#dc2626" if res.payload_total > 20 else ("#d97706" if res.safety_margin_kg < calc.LOW_MARGIN_KG else "#16a34a")
            load_color = "#dc2626" if res.bottleneck else ("#d97706" if res.above_benchmark else "#16a34a")
            g1, g2 = st.columns(2)
            with g1:
                bullet(res.payload_total, max(25.0, res.payload_total * 1.1), 20.0, payload_color, " kg",
                       "Sarcină UR20 (găleată + gripper) — linia neagră = limita 20 kg")
            with g2:
                bullet(res.load_pct, max(150.0, res.load_pct * 1.1), 100.0, load_color, " %",
                       f"Încărcare vs. reper {calc.fmt_num(res.benchmark_bpm)} găleți/min — linia neagră = 100%")
            if res.payload_total > calc.UR20_MAX_PAYLOAD_KG:
                st.error(f"🔴 SUPRASARCINĂ: {calc.fmt_num(res.payload_total)} kg > 20 kg — configurație incompatibilă UR20.")
            if res.bottleneck:
                st.warning("⚠️ Gâtuire: debit > 8,6 găleți/min. **Recomandare: 2 celule UR20 în paralel sau analiză flux amonte/aval.**")
            elif res.above_benchmark:
                st.warning(f"⚠️ Debitul depășește reperul testat de {calc.fmt_num(res.benchmark_bpm)} găleți/min pentru această greutate — necesită test de cadență.")

        # Section 3
        with st.container(border=True):
            st.markdown("##### 3. Protocol Om–Robot")
            m = st.columns(3)
            m[0].metric("Selecție preluare", inp.side_selection)
            m[1].metric("Fereastră schimb palet", f"{calc.fmt_num(res.fill_time_min)} min",
                        help=f"{inp.buckets_per_pallet} găleți / min(debit linie, reper testat {calc.fmt_num(res.benchmark_bpm)})")
            m[2].metric("Interval separator manual", f"{calc.fmt_num(res.separator_time_min)} min",
                        help=f"({inp.buckets_per_pallet} / {inp.layers} straturi) / min(debit linie, reper testat)")
            t = st.columns(2)
            t[0].metric("Tone ridicate manual azi / schimb", f"{calc.fmt_num(res.manual_tonnes_shift)} t",
                        help=f"{calc.fmt_num(inp.line_rate_bpm, 2)} găleți/min × 60 × 8 h × {calc.fmt_num(inp.bucket_weight_kg)} kg — {calc.LABEL_ESTIMATE}")
            t[1].metric("Ridicări / minut / operator", calc.fmt_num(res.manual_lifts_per_min_operator),
                        help="Ipoteză: 2 operatori pe schimb, ca la PURATOS înainte de automatizare")
            sections = report_builder.report_sections(res)
            for k, v in sections["s3"]:
                if k in ("Selecție preluare operator", "Configurație palet", "Siguranță"):
                    st.markdown(f"- **{k}:** {v}")
            st.info(
                "**Manual (operator):** schimbarea paleților și așezarea separatoarelor.  \n"
                "**În afara scopului celulei automate:** transport autonom MiR (AGV/AMR), înfoliere, expediere."
            )

        # Section 4
        with st.container(border=True):
            st.markdown("##### 4. Echipare & Riscuri Specifice")
            st.dataframe(pd.DataFrame(res.hardware, columns=["Echipament", "Status"]), hide_index=True,
                         width="stretch")
            st.markdown("**Riscuri detectate automat și semnalate:**")
            if res.risks:
                for r in res.risks:
                    icon = "🔴" if r.title == "Suprasarcină UR20" else ("💬" if r.source == "chat" else "⚠️")
                    st.markdown(f"- {icon} **{r.title}:** {r.detail}")
            else:
                st.markdown("- ✅ Niciun risc critic detectat pe baza ipotezelor introduse.")
            for n in res.notes:
                st.caption(f"ℹ️ {n}")
            st.markdown("**🔒 Confidențial / De verificat on-site:**")
            if inp.confidential_fields:
                st.markdown("\n".join(f"- {c}" for c in inp.confidential_fields))
            else:
                st.caption("Niciun câmp marcat.")

        # Section 5
        with st.container(border=True):
            st.markdown("##### 5. Alocare Hub Tech-Con & Pași Următori")
            st.success(f"📍 Hub alocat: **{res.hub}** (județ {inp.county})")
            st.markdown("\n".join(f"{i}. {a}" for i, a in enumerate(calc.ONSITE_ACTIONS, 1)))

        # Export controls
        report_md = report_builder.build_markdown(res)
        report_html = report_builder.build_html(res)
        e1, e2 = st.columns(2)
        e1.download_button(
            "⬇️ Descarcă Raport Printabil (HTML / Print-to-PDF)", data=report_html.encode("utf-8"),
            file_name="pre-audit-ur20.html", mime="text/html", width="stretch", type="primary",
        )
        e2.download_button(
            "⬇️ Descarcă Text Raport (.md)", data=report_md.encode("utf-8"),
            file_name="pre-audit-ur20.md", mime="text/markdown", width="stretch",
        )
        with st.expander("📋 Copiază / Descarcă Text Raport"):
            st.caption("Folosiți butonul de copiere din colțul blocului de mai jos.")
            st.code(report_md, language="markdown")
            st.download_button("⬇️ Descarcă .txt", data=report_md.encode("utf-8"), file_name="pre-audit-ur20.txt",
                               mime="text/plain")

        # ------------------------------------------------------------------
        # Lead form
        # ------------------------------------------------------------------
        st.markdown("### 📨 Trimite cererea către Tech-Con (demo, date fictive)")
        with st.form("lead_form", clear_on_submit=False):
            l1, l2 = st.columns(2)
            company = l1.text_input("Nume firmă fictivă", placeholder="Ex: Lactate Demo SRL")
            role = l2.selectbox("Rol contact", ["Director Producție", "Inginer Automatist", "Manager Mentenanță", "Director General"])
            email = st.text_input("Email de test", placeholder="Ex: demo@exemplu-fictiv.ro")
            confirm = st.checkbox("Confirm că am introdus exclusiv date fictive de test (nu date reale).")
            submit_lead = st.form_submit_button("💾 Salvează cererea în Mini-CRM", type="primary")
        if submit_lead:
            lead_errors = []
            if not company.strip():
                lead_errors.append("Completați numele firmei fictive.")
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", email.strip()):
                lead_errors.append("Introduceți un email de test valid (ex: demo@exemplu-fictiv.ro).")
            elif email.strip().lower().split("@")[-1] in {
                "gmail.com", "yahoo.com", "yahoo.ro", "outlook.com", "hotmail.com", "icloud.com", "live.com", "proton.me",
            }:
                lead_errors.append("Folosiți un domeniu de email fictiv (ex: @exemplu-fictiv.ro), nu o adresă reală.")
            if not confirm:
                lead_errors.append("Bifați confirmarea că datele sunt fictive.")
            if lead_errors:
                st.error("\n".join(f"- {e}" for e in lead_errors))
            else:
                lead_id = database.insert_lead({
                    "company": company.strip()[:120], "contact_role": role, "email": email.strip()[:120],
                    "industry": inp.industry, "bucket_weight_kg": inp.bucket_weight_kg,
                    "gripper_weight_kg": inp.gripper_weight_kg, "payload_total": res.payload_total,
                    "line_rate_bpm": inp.line_rate_bpm, "side_selection": inp.side_selection, "shifts": inp.shifts,
                    "county": inp.county, "hub": res.hub, "verdict": res.verdict_crm, "score": res.score,
                    "payback": res.payback,
                    "params_json": json.dumps({
                        "content_type": inp.content_type, "has_handle": inp.has_handle, "air_supply": inp.air_supply,
                        "pallet_equipment": inp.pallet_equipment, "pallet": inp.pallet_config,
                        "buckets_per_pallet": inp.buckets_per_pallet, "layers": inp.layers,
                        "load_pct": round(res.load_pct, 1), "confidential_fields": inp.confidential_fields,
                        "custom_risks": inp.custom_risks,
                    }, ensure_ascii=False),
                })
                ss.flash.append(("success", f"✅ Cererea #{lead_id} a fost salvată în Mini-CRM (hub {res.hub}, verdict {res.verdict_crm}). Vedeți tabul «Cereri Relevante Tech-Con»."))
                st.rerun()

# ==========================================================================
# 7. CRM TAB
# ==========================================================================
with tab_crm:
    st.markdown("#### 📇 Cereri Relevante Tech-Con (Demo CRM)")
    st.caption("Toate înregistrările sunt fictive. Primele 3 cereri sunt date demo pre-încărcate.")
    leads = database.get_leads()
    fc1, fc2 = st.columns(2)
    hub_filter = fc1.multiselect("Filtru Hub", calc.HUBS, default=calc.HUBS, key="crm_hub")
    verdict_filter = fc2.multiselect("Filtru Verdict", ["Verde", "Galben", "Roșu"], default=["Verde", "Galben", "Roșu"], key="crm_verdict")
    view = leads[leads["hub"].isin(hub_filter) & leads["verdict"].isin(verdict_filter)]

    k = st.columns(4)
    k[0].metric("Cereri afișate", len(view), help=f"Total în baza de date: {len(leads)}")
    k[1].metric("🟢 Verde", int((view["verdict"] == "Verde").sum()))
    k[2].metric("🟡 Galben", int((view["verdict"] == "Galben").sum()))
    k[3].metric("🔴 Roșu", int((view["verdict"] == "Roșu").sum()))
    if len(view):
        st.caption(f"Scor mediu potrivire: **{view['score'].mean():.0f}/100** · " +
                   " · ".join(f"{h}: {int((view['hub'] == h).sum())}" for h in calc.HUBS))

    if view.empty:
        st.info("Nicio cerere pentru filtrele selectate.")
    else:
        table = view[["id", "created_at", "company", "contact_role", "email", "industry", "payload_total",
                      "line_rate_bpm", "side_selection", "shifts", "county", "hub", "verdict", "score", "payback"]].rename(columns={
            "id": "ID", "created_at": "Data", "company": "Firmă (fictivă)", "contact_role": "Rol", "email": "Email test",
            "industry": "Industrie", "payload_total": "Sarcină (kg)", "line_rate_bpm": "Debit (găl./min)",
            "side_selection": "Preluare", "shifts": "Schimburi", "county": "Județ", "hub": "Hub", "verdict": "Verdict",
            "score": "Scor", "payback": "Amortizare",
        })
        table["Verdict"] = table["Verdict"].map({"Verde": "🟢 Verde", "Galben": "🟡 Galben", "Roșu": "🔴 Roșu"})
        st.dataframe(
            table, hide_index=True, width="stretch",
            column_config={
                "Scor": st.column_config.ProgressColumn("Scor", min_value=0, max_value=100, format="%d"),
                "Sarcină (kg)": st.column_config.NumberColumn(format="%.1f"),
                "Debit (găl./min)": st.column_config.NumberColumn(format="%.2f"),
            },
        )
        st.download_button(
            "⬇️ Exportă cererile filtrate (CSV)", data=view.drop(columns=["params_json"]).to_csv(index=False).encode("utf-8-sig"),
            file_name="cereri-ur20-demo.csv", mime="text/csv",
        )

        with st.expander("🔍 Detalii cerere / ștergere"):
            options = view["id"].tolist()
            sel = st.selectbox("Selectați cererea", options,
                               format_func=lambda i: f"#{i} — {view.loc[view['id'] == i, 'company'].iloc[0]}", key="crm_sel")
            row = view[view["id"] == sel].iloc[0]
            st.markdown(f"**{row['company']}** · {row['contact_role']} · {row['email']}  \n"
                        f"Hub **{row['hub']}** · Verdict **{row['verdict']}** · Scor **{row['score']}/100** · Amortizare {row['payback']}")
            try:
                st.json(json.loads(row["params_json"]), expanded=False)
            except (TypeError, ValueError):
                pass
            if st.button(f"🗑️ Șterge cererea #{sel}", key="crm_delete"):
                database.delete_lead(int(sel))
                ss.flash.append(("info", f"Cererea #{sel} a fost ștearsă."))
                st.rerun()

    with st.expander("⚙️ Administrare demo"):
        st.caption("Readuce baza de date la cele 3 cereri fictive inițiale.")
        if st.button("↺ Resetează datele demo CRM", key="crm_reset"):
            database.reset_demo_data()
            ss.flash.append(("info", "Datele demo CRM au fost resetate (3 cereri fictive)."))
            st.rerun()
