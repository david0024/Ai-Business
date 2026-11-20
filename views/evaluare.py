"""Evaluation form + benefits report (deterministic)."""
import json
from datetime import datetime

import streamlit as st

import calculator as calc
import database
import ui

FMT = calc.fmt_num
BPP_BY_WEIGHT = {5.0: 100, 13.0: 44}


def _report_html(seg, county, inputs, b) -> str:
    rows = "".join(f"<tr><td>{k}</td><td><b>{v}</b></td></tr>" for k, v in inputs.items())
    return f"""<!doctype html><html lang="ro"><meta charset="utf-8"><title>Raport PaletCheck UR20</title>
<style>body{{font-family:system-ui,Arial;color:#0A0F1C;max-width:760px;margin:24px auto;padding:0 16px}}
h1{{color:#0B5FFF}}td{{padding:4px 10px;border-bottom:1px solid #E3E8F0}}.k{{font-size:1.4rem;font-weight:800;color:#0B5FFF}}
.box{{border:1px solid #E3E8F0;border-radius:12px;padding:12px;margin:10px 0}}small{{color:#5B6475}}</style>
<h1>Raport de beneficii · PaletCheck UR20</h1>
<p>{datetime.now():%Y-%m-%d %H:%M} · DATE FICTIVE · {seg} · județ {county}</p>
<table>{rows}</table>
<div class="box"><b>1. Bani: capacitate și recuperare</b><br><span class="k">{b['payback_lo']}–{b['payback_hi']} luni</span>
 fereastră orientativă de recuperare (interval general 18–40 luni, preț scenariu 130.000 EUR fără TVA).<br>
 Capacitate de paletizare disponibilă: +{FMT(b['headroom_day'],0)} găleți/zi (~{FMT(b['headroom_t_year'],0)} t/an).</div>
<div class="box"><b>2. Timp câștigat</b><br><span class="k">{FMT(b['freed_hours_day'],0)} ore-operator/zi</span>
 redirecționate (~{FMT(b['freed_hours_year'],0)} ore/an). Fereastră de schimb palet: {FMT(b['pallet_window_min'])} min.</div>
<div class="box"><b>3. Oameni</b><br><span class="k">{FMT(b['tonnes_shift'])} t/schimb</span>
 nu mai sunt ridicate manual ({FMT(b['tonnes_per_operator_shift'])} t și {FMT(b['lifts_per_operator_shift'],0)} ridicări per operator).
 ~{FMT(b['tonnes_year'],0)} t/an.</div>
<div class="box"><b>4. Calitate și siguranță</b><br>Paletizare după model programat, repetabilă; 3 scanere de siguranță.</div>
<small>Rezultate de test PURATOS — nu reprezintă garanții universale: 7,4 găleți/min (13 kg), 8,6 găleți/min (5 kg).<br>
Estimare bazată pe ipotezele introducerii: gripper 5 kg, {calc.WORKING_DAYS_PER_YEAR} zile/an, schimb palet {FMT(calc.PALLET_CHANGE_MIN)} min,
separator {FMT(calc.SEPARATOR_MIN_PER_LAYER)} min/strat, disponibilitate {int(calc.CELL_AVAILABILITY*100)}%.<br>
Nu se calculează economii salariale sau ROI personalizat. În afara ofertei: MiR (AGV/AMR), înfoliere, expediere.</small></html>"""


def _pillar(col, tag, title, big, text):
    col.markdown(f'<div class="pc-card"><span class="pc-tag est">{tag}</span><h4>{title}</h4>'
                 f'<div class="big">{big}</div><p>{text}</p></div>', unsafe_allow_html=True)


def render() -> None:
    ss = st.session_state
    ui.banner()
    st.markdown('<div class="pc-eyebrow">Evaluare gratuită · 2 minute</div>', unsafe_allow_html=True)
    st.title("Ce câștigă linia dvs. cu o celulă UR20")
    st.caption("Introduceți datele actuale ale liniei (fictive). Raportul apare imediat sub formular.")

    with st.form("eval_form"):
        seg = st.selectbox("Ramura de producție", calc.SEGMENTS, index=calc.SEGMENTS.index(ss.segment))
        c1, c2 = st.columns(2)
        weight = c1.number_input("Greutatea găleții pline (kg)", value=13.0, step=0.5, min_value=None)
        rate = c2.number_input("Ritmul actual al liniei (găleți/min)", value=6.0, step=0.1)
        shifts = c1.selectbox("Schimburi pe zi", [1, 2, 3], index=2)
        hours = c2.number_input("Ore pe schimb", value=8.0, step=0.5)
        operators = c1.number_input("Operatori la paletizare / schimb", value=2, step=1)
        bpp = c2.number_input("Găleți pe palet", value=44, step=1)
        county = st.selectbox("Județul fabricii", calc.COUNTIES, index=calc.COUNTIES.index("Ilfov"))
        go_ = st.form_submit_button("Generează raportul", type="primary", use_container_width=True)
    c_ok, c_bad = st.columns(2)
    if c_ok.button("Exemplu: caz normal (13 kg, 6/min)", use_container_width=True):
        ss.eval_inputs = dict(seg=calc.SEGMENTS[0], weight=13.0, rate=6.0, shifts=3, hours=8.0, operators=2, bpp=44, county="Ilfov")
    if c_bad.button("Exemplu: date lipsă / greșite", use_container_width=True):
        ss.eval_inputs = dict(seg=calc.SEGMENTS[1], weight=None, rate=0.0, shifts=3, hours=14.0, operators=0, bpp=44, county="Brașov")
    if go_:
        ss.segment = seg
        ss.eval_inputs = dict(seg=seg, weight=weight, rate=rate, shifts=shifts, hours=hours,
                              operators=operators, bpp=bpp, county=county)

    data = ss.get("eval_inputs")
    if data:
        _show_report(data)
    ui.chat_widget()
    ui.footer()


def _show_report(d) -> None:
    errs = calc.validate_benefits_input(d["weight"], d["rate"], d["hours"], d["shifts"], d["operators"], d["bpp"])
    st.divider()
    if errs:
        st.error("**Raportul nu poate fi generat. Corectați datele:**\n\n" + "\n".join(f"- {e}" for e in errs))
        return
    b = calc.benefits(float(d["weight"]), float(d["rate"]), float(d["hours"]), int(d["shifts"]),
                      int(d["operators"]), int(d["bpp"]))
    hub = calc.hub_for_county(d["county"])
    st.subheader("Raportul dvs. de beneficii")
    if not b["eligible"]:
        st.error(f"Găleata ({FMT(d['weight'])} kg) + gripperul (5 kg) = {FMT(b['payload'])} kg depășesc sarcina UR20 "
                 "de 20 kg. Configurația este în afara cazului de referință; discutați un format mai mic.")
        return
    if b["bottleneck"]:
        st.warning(f"Linia dă {FMT(d['rate'])} găleți/min, peste ritmul testat de {FMT(b['benchmark'])}. "
                   "O celulă ar deveni blocajul: evaluăm 2 celule în paralel.")
    else:
        st.success(f"Potrivire probabilă. Linia folosește {FMT(b['load_pct'], 0)}% din ritmul testat de "
                   f"{FMT(b['benchmark'])} găleți/min. Evaluarea tehnică o face biroul **{hub}**.")

    r1 = st.columns(2)
    _pillar(r1[0], "Bani", "Recuperare & capacitate", f"{b['payback_lo']}–{b['payback_hi']} luni",
            f"Fereastră orientativă pentru {d['shifts']} schimb(uri), la 130.000 EUR fără TVA. Celula mai are "
            f"<b>+{FMT(b['headroom_day'], 0)} găleți/zi</b> capacitate (~{FMT(b['headroom_t_year'], 0)} t/an) "
            "dacă linia din amonte crește.")
    _pillar(r1[1], "Timp", "Ore-operator eliberate", f"{FMT(b['freed_hours_day'], 0)} h/zi",
            f"Din {FMT(b['op_hours_now_day'], 0)} h/zi de paletizare manuală rămân ~{FMT(b['op_hours_cell_day'], 0)} h "
            f"pentru schimb palet și separatoare (~{FMT(b['freed_hours_year'], 0)} h/an). Operatorul are "
            f"{FMT(b['pallet_window_min'])} min să schimbe paletul.")
    r2 = st.columns(2)
    _pillar(r2[0], "Oameni", "Greutate neridicată", f"{FMT(b['tonnes_shift'])} t/schimb",
            f"{FMT(b['tonnes_per_operator_shift'])} t și {FMT(b['lifts_per_operator_shift'], 0)} ridicări per operator "
            f"pe schimb nu mai sunt făcute manual (~{FMT(b['tonnes_year'], 0)} t/an).")
    _pillar(r2[1], "Calitate", "Paleți identici, zonă sigură", "100% model programat",
            "Fiecare palet urmează aceeași schemă. 3 scanere încetinesc sau opresc robotul când intră cineva în zonă.")
    st.caption("Rezultate de test PURATOS — nu reprezintă garanții universale. Restul: estimare bazată pe ipotezele "
               "introducerii. Nu calculăm economii salariale sau ROI personalizat (cerință a temei).")

    inputs = {"Ramură": d["seg"], "Greutate găleată": f"{FMT(d['weight'])} kg", "Ritm linie": f"{FMT(d['rate'])} găleți/min",
              "Schimburi": f"{d['shifts']} × {FMT(d['hours'])} h", "Operatori/schimb": d["operators"],
              "Găleți/palet": d["bpp"]}
    a, c = st.columns(2)
    a.download_button("Descarcă raportul (HTML)", _report_html(d["seg"], d["county"], inputs, b), icon=":material/download:",
                      file_name="raport-paletcheck-ur20.html", mime="text/html", use_container_width=True)
    with c.popover("Cere evaluarea tehnică", icon=":material/send:", use_container_width=True):
        with st.form("lead_form", border=False):
            company = st.text_input("Companie (fictivă)")
            email = st.text_input("E-mail de test", placeholder="test@exemplu.ro")
            role = st.selectbox("Rol", ["Director de producție", "Director tehnic", "Responsabil investiții"])
            ok = st.checkbox("Confirm că datele sunt fictive")
            sent = st.form_submit_button("Trimite cererea", type="primary", use_container_width=True)
        if sent:
            if len(company.strip()) < 2 or not ui.EMAIL_RE.match(email.strip()) or not ok:
                st.error("Completați compania, un e-mail valid și bifați confirmarea.")
            else:
                inp = calc.SimulationInput(industry=calc.INDUSTRY_NONFOOD if d["seg"] == calc.SEGMENTS[3] else calc.INDUSTRY_FOOD,
                                           bucket_weight_kg=float(d["weight"]), line_rate_bpm=float(d["rate"]),
                                           shifts=int(d["shifts"]), county=d["county"])
                res = calc.simulate(inp)
                lead_id = database.insert_lead({
                    "company": company.strip(), "contact_role": role, "email": email.strip(),
                    "industry": inp.industry, "bucket_weight_kg": inp.bucket_weight_kg,
                    "gripper_weight_kg": inp.gripper_weight_kg, "payload_total": res.payload_total,
                    "line_rate_bpm": inp.line_rate_bpm, "side_selection": inp.side_selection,
                    "shifts": inp.shifts, "county": inp.county, "hub": res.hub, "verdict": res.verdict_crm,
                    "score": res.score, "payback": res.payback,
                    "params_json": json.dumps({"segment": d["seg"], **{k: str(v) for k, v in d.items()}}, ensure_ascii=False),
                })
                st.success(f"Cererea #{lead_id} a ajuns în Mini-CRM, la biroul {res.hub}.")
