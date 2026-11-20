"""Shared UI pieces: theme CSS, warning banner, robot-arm SVG, floating assistant, footer."""
from __future__ import annotations

import base64
import re

import streamlit as st

import ai_consultant
import calculator as calc
import database

BLUE = "#0B5FFF"
INK = "#0A0F1C"

CSS = f"""
<style>
:root {{ --blue:{BLUE}; --ink:{INK}; --muted:#5B6475; --line:#E3E8F0; --soft:#F2F6FC; }}
.block-container {{ padding-top:1rem; padding-bottom:2rem; max-width:1100px; }}
h1,h2,h3 {{ color:var(--ink); letter-spacing:-0.02em; }}
.pc-banner {{ background:var(--ink); color:#fff; border-radius:10px; padding:8px 14px; font-size:.86rem; margin-bottom:.8rem; }}
.pc-banner b {{ color:#9DB8FF; }}
.pc-eyebrow {{ color:var(--blue); font-weight:700; font-size:.8rem; letter-spacing:.08em; text-transform:uppercase; }}
.pc-hero h1 {{ color:var(--ink) !important; font-size:clamp(2rem, 5vw, 3.1rem); line-height:1.08; margin:.3rem 0 .8rem; padding:0; }}
.pc-hero h1 span {{ color:var(--blue); }}
.pc-lead {{ font-size:1.08rem; color:var(--muted); line-height:1.55; max-width:34rem; }}
.pc-stats {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin:1.2rem 0; }}
.pc-stat {{ border:1px solid var(--line); border-radius:14px; padding:14px; background:#fff; }}
.pc-stat .v {{ font-size:1.5rem; font-weight:800; color:var(--ink); }}
.pc-stat .l {{ font-size:.82rem; color:var(--muted); line-height:1.35; }}
.pc-card {{ border:1px solid var(--line); border-radius:16px; padding:18px; background:#fff; height:100%; }}
.pc-card h4 {{ margin:0 0 .4rem; padding:0; font-size:1.02rem; }}
.pc-card .big {{ font-size:1.7rem; font-weight:800; color:var(--blue); line-height:1.1; }}
.pc-card p, .pc-card li {{ color:var(--muted); font-size:.92rem; line-height:1.45; }}
.pc-tag {{ display:inline-block; font-size:.7rem; font-weight:700; border-radius:999px; padding:2px 9px; margin-bottom:6px; }}
.pc-tag.fact {{ background:#E6EEFF; color:#0B3FB0; }}
.pc-tag.est {{ background:#F1F2F4; color:#30343B; }}
.pc-steps {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }}
.pc-step {{ border-top:3px solid var(--blue); padding:10px 2px; }}
.pc-step b {{ display:block; margin-bottom:2px; }}
.pc-step span {{ color:var(--muted); font-size:.9rem; }}
.st-key-pc_footer {{ background:var(--soft); border-top:4px solid var(--ink); border-radius:18px; padding:22px; margin-top:2.5rem; }}
.pc-feed {{ border:1px solid var(--line); border-radius:14px; padding:14px 16px; margin-bottom:10px; background:#fff; }}
.pc-feed .t {{ font-weight:700; color:var(--ink); }}
.pc-feed .m {{ font-size:.78rem; color:var(--blue); font-weight:700; text-transform:uppercase; letter-spacing:.05em; }}
.pc-feed p {{ margin:.25rem 0 .35rem; color:var(--muted); font-size:.9rem; }}
/* Streamlit buttons: primary = blue, secondary = ink outline */
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primaryFormSubmit"], [data-testid="stPageLink"] a {{ border-radius:999px; font-weight:700; }}
.st-key-cta a {{ background:var(--blue); color:#fff !important; border-radius:999px; padding:.7rem 1.4rem; justify-content:center; }}
.st-key-cta a:hover {{ background:#0848CC; }}
.st-key-cta a p {{ color:#fff !important; font-weight:700; font-size:1.02rem; }}
/* Floating assistant, bottom-right */
.st-key-pc_chat {{ position:fixed; right:18px; bottom:18px; z-index:9999; width:auto !important; }}
.st-key-pc_chat button {{ background:var(--blue); color:#fff; border:none; border-radius:999px; padding:.65rem 1.1rem;
  box-shadow:0 10px 30px rgba(11,95,255,.35); font-weight:700; }}
@media (max-width: 640px) {{
  .pc-stats, .pc-steps {{ grid-template-columns:1fr; }}
  .st-key-pc_chat {{ right:10px; bottom:10px; }}
}}
</style>
"""


def setup() -> None:
    database.init_db()
    st.markdown(CSS, unsafe_allow_html=True)
    ss = st.session_state
    ss.setdefault("segment", calc.SEGMENTS[0])
    ss.setdefault("pc_chat", [])


def banner() -> None:
    st.markdown(
        '<div class="pc-banner">⚠️ <b>Prototip demonstrativ.</b> Nu introduceți date personale reale sau '
        "informații confidențiale ale companiei. Folosiți doar <b>date de test fictive</b>.</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Robot arm: pure SVG + CSS, only the arm moves up and down.
# --------------------------------------------------------------------------
ROBOT_ARM_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 460 380" role="img" aria-label="Braț robotic colaborativ UR20 care se mișcă sus-jos">
<style>
.upper, .fore, .wrist {{ transform-box:view-box; animation-duration:3.4s;
  animation-iteration-count:infinite; animation-timing-function:cubic-bezier(.45,0,.55,1); }}
.upper {{ transform-origin:130px 262px; animation-name:pcUpper; }}
.fore  {{ transform-origin:250px 132px; animation-name:pcFore; }}
.wrist {{ transform-origin:360px 160px; animation-name:pcWrist; }}
.shadow {{ transform-box:fill-box; transform-origin:center; animation:pcShadow 3.4s infinite cubic-bezier(.45,0,.55,1); }}
@keyframes pcUpper {{ 0%,100% {{ transform:rotate(-7deg); }} 50% {{ transform:rotate(6deg); }} }}
@keyframes pcFore  {{ 0%,100% {{ transform:rotate(-9deg); }} 50% {{ transform:rotate(14deg); }} }}
@keyframes pcWrist {{ 0%,100% {{ transform:rotate(16deg); }} 50% {{ transform:rotate(-20deg); }} }}
@keyframes pcShadow {{ 0%,100% {{ transform:scaleX(.8); opacity:.10; }} 50% {{ transform:scaleX(1.05); opacity:.22; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation:none !important; }} }}
</style>
  <defs>
    <linearGradient id="tube" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF"/><stop offset=".55" stop-color="#E9EEF6"/><stop offset="1" stop-color="#C9D3E3"/>
    </linearGradient>
    <linearGradient id="cap" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#3D82FF"/><stop offset="1" stop-color="{BLUE}"/>
    </linearGradient>
    <linearGradient id="base" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#1A2233"/><stop offset=".5" stop-color="#2B3548"/><stop offset="1" stop-color="#0A0F1C"/>
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="460" height="380" rx="28" fill="#F2F6FC"/>
  <ellipse class="shadow" cx="360" cy="344" rx="70" ry="9" fill="{INK}"/>
  <!-- pedestal -->
  <rect x="88" y="300" width="84" height="48" rx="8" fill="url(#base)"/>
  <rect x="78" y="340" width="104" height="12" rx="5" fill="{INK}"/>
  <rect x="100" y="270" width="60" height="34" rx="10" fill="url(#tube)" stroke="#B8C4D6"/>
  <g class="upper">
    <!-- upper arm -->
    <line x1="130" y1="262" x2="250" y2="132" stroke="#B8C4D6" stroke-width="44" stroke-linecap="round"/>
    <line x1="130" y1="262" x2="250" y2="132" stroke="url(#tube)" stroke-width="40" stroke-linecap="round"/>
    <circle cx="130" cy="262" r="30" fill="url(#cap)"/><circle cx="130" cy="262" r="12" fill="{INK}"/>
    <g class="fore">
      <!-- forearm -->
      <line x1="250" y1="132" x2="360" y2="160" stroke="#B8C4D6" stroke-width="34" stroke-linecap="round"/>
      <line x1="250" y1="132" x2="360" y2="160" stroke="url(#tube)" stroke-width="30" stroke-linecap="round"/>
      <circle cx="250" cy="132" r="25" fill="url(#cap)"/><circle cx="250" cy="132" r="10" fill="{INK}"/>
      <g class="wrist">
        <circle cx="360" cy="160" r="19" fill="url(#cap)"/><circle cx="360" cy="160" r="7" fill="{INK}"/>
        <rect x="350" y="176" width="20" height="28" rx="6" fill="url(#tube)" stroke="#B8C4D6"/>
        <!-- gripper -->
        <rect x="326" y="202" width="68" height="12" rx="4" fill="{INK}"/>
        <rect x="328" y="212" width="9" height="26" rx="3" fill="#2B3548"/>
        <rect x="383" y="212" width="9" height="26" rx="3" fill="#2B3548"/>
        <!-- bucket -->
        <path d="M333 236 h54 l-6 56 h-42 z" fill="#FFFFFF" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"/>
        <rect x="331" y="230" width="58" height="9" rx="3" fill="{BLUE}"/>
        <path d="M341 254 h38" stroke="#C9D3E3" stroke-width="2"/>
      </g>
    </g>
  </g>
</svg>"""


def robot_arm() -> None:
    data = base64.b64encode(ROBOT_ARM_SVG.encode("utf-8")).decode("ascii")
    st.markdown(
        f'<img src="data:image/svg+xml;base64,{data}" alt="Braț robotic UR20 animat" '
        'style="width:100%;max-width:470px;display:block;margin:0 auto">',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Floating assistant (bottom-right), deterministic answers + optional LLM
# --------------------------------------------------------------------------
SEGMENT_INTRO = {
    calc.SEGMENTS[0]: "Cel mai apropiat caz de PURATOS: găleți de 5–13 kg cu umpluturi, creme sau glazuri. "
                      "Ritmurile testate (7,4 și 8,6 găleți/min) se aplică direct ca reper.",
    calc.SEGMENTS[1]: "Telemea și brânzeturi în saramură: verificăm greutatea găleții pline cu saramură (max. 15 kg "
                      "cu gripper de 5 kg) și cerințele de spălare și igienă.",
    calc.SEGMENTS[2]: "Sosuri și maioneză pentru HoReCa: de obicei găleți de 5–10 kg, deci sub limita de sarcină. "
                      "Validăm stabilitatea capacului și forma găleții.",
    calc.SEGMENTS[3]: "Vopsele și tencuieli: doar formatele de până la 10 L se încadrează. Găleata de 15 L (~20 kg) plus "
                      "gripperul depășește sarcina UR20 de 20 kg.",
}

EXTRA_QA = [
    (r"\b(incep|formular|evaluare|cum procedez|pasul urmator|demo)\b",
     "Apăsați „Evaluează-ți linia” din pagina principală: completați 6 câmpuri și primiți imediat raportul de beneficii. "
     "La final puteți trimite cererea de evaluare tehnică."),
    (r"\b(igien\w*|spalar\w*|washdown|curatenie)\b",
     "Cerințele de igienă și spălare se validează separat la evaluarea tehnică (materiale, protecție IP, procedură de curățare)."),
    (r"\b(spatiu|dimensiun\w*|amprent\w*|m2|metri)\b",
     "Celula are robotul, transportorul de alimentare și 2 poziții de paletizare pe europaleți, cu zone monitorizate de 3 scanere. "
     "Amprenta exactă se măsoară la auditul on-site."),
    (r"\b(grant\w*|finantar\w*|fonduri|pnrr)\b",
     "În 2026 există apeluri pentru IMM-uri inovatoare (granturi de 200.000–3 mil. EUR pentru AI și robotică). "
     "Eligibilitatea se verifică cu un consultant de finanțare."),
    (r"\b(service|mentenant\w*|garantie|suport)\b",
     "Service-ul și instruirea operatorilor sunt asigurate din birourile Tech-Con din Dragomirești-Deal, Iași și Timișoara."),
    (r"\b(debit\w* fabric\w*|blocaj\w*|productie mai mare|mai rapid)\b",
     "Un robot mai rapid nu crește automat debitul fabricii. Dacă linia dă sub ritmul testat, limita e în amonte (umplere, transportor)."),
]

QUICK_QUESTIONS = [
    "Cât de repede paletizează?",
    "Cât costă și în cât timp se recuperează?",
    "Ce rămâne manual?",
    "Ce nu este inclus?",
]


def _strip(text: str) -> str:
    return calc.strip_diacritics(text)


def assistant_reply(text: str) -> str:
    t = _strip(text)
    if re.search(r"\b(manual\w*|operator\w*)\b", t):
        return ("Schimbarea paleților plini și așezarea separatoarelor rămân manuale. Robotul preia găleata de pe "
                "transportor și o așază pe una dintre cele 2 poziții, iar operatorul lucrează în siguranță pe cealaltă.")
    for pattern, answer in EXTRA_QA:
        if re.search(pattern, t):
            return answer
    for pattern, answer in ai_consultant.QA_TOPICS:
        if re.search(pattern, t):
            return answer
    if re.search(r"\b(repede|ritm|cadent\w*|viteza|paletizeaza)\b", t):
        return ai_consultant.QA_TOPICS[8][1]
    if re.search(r"\b(inclus|nu este|lipseste|scop)\b", t):
        return ai_consultant.QA_TOPICS[5][1]
    return ("Nu am un răspuns verificat la această întrebare. Pot explica ritmurile testate, sarcina UR20, prețul, "
            "livrarea, siguranța, ce rămâne manual sau ce nu este inclus. Pentru restul, cereți evaluarea tehnică.")


def _ask(text: str) -> None:
    st.session_state.pc_chat += [("user", text), ("assistant", assistant_reply(text))]


def _on_segment_pick() -> None:
    seg = st.session_state.get("pc_chat_segment")
    if seg:
        st.session_state.segment = seg
        st.session_state.pc_chat += [("user", f"Compania mea: {seg}"), ("assistant", SEGMENT_INTRO[seg])]


def chat_widget() -> None:
    ss = st.session_state
    with st.container(key="pc_chat"):
        with st.popover("💬 Asistent UR20"):
            st.markdown("**Asistent PaletCheck** · răspunsuri verificate din studiul de caz")
            st.pills("Tipul companiei", calc.SEGMENTS, key="pc_chat_segment", on_change=_on_segment_pick)
            box = st.container(height=240)
            with box:
                if not ss.pc_chat:
                    st.caption("Alegeți tipul companiei sau puneți o întrebare. Calculele sunt făcute în Python, nu de AI.")
                for role, msg in ss.pc_chat[-8:]:
                    st.chat_message(role, avatar="🧑‍🏭" if role == "user" else "🤖").write(msg)
            cols = st.columns(2)
            for i, q in enumerate(QUICK_QUESTIONS):
                cols[i % 2].button(q, key=f"pcq_{i}", on_click=_ask, args=(q,), use_container_width=True)
            with st.form("pc_chat_form", clear_on_submit=True, border=False):
                text = st.text_input("Întrebarea dvs.", placeholder="Ex.: Merge pentru găleți de 10 kg?",
                                     label_visibility="collapsed")
                if st.form_submit_button("Trimite", type="primary", use_container_width=True):
                    if text.strip():
                        _ask(text.strip())
                        st.rerun()
                    else:
                        st.warning("Scrieți o întrebare.")
            if ss.pc_chat and st.button("Șterge conversația", key="pc_chat_clear"):
                ss.pc_chat = []
                st.rerun()


# --------------------------------------------------------------------------
# Footer with working newsletter sign-up
# --------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


def footer() -> None:
    with st.container(key="pc_footer"):
        c1, c2 = st.columns([1.1, 1])
        with c1:
            st.markdown("##### PaletCheck UR20 · Tech-Con România")
            st.markdown(
                "Birouri: **Dragomirești-Deal (Ilfov)** · **Iași** · **Timișoara**  \n"
                "Paletizare automată a găleților cu robotul colaborativ Universal Robots UR20.  \n"
                "Rețele sociale *(conturi fictive, doar pentru demo)*: "
                "LinkedIn **@paletcheck-ur20** · YouTube **@PaletCheckUR20** · Facebook **/PaletCheckRO**"
            )
            st.caption("Prototip SYSUP 2026. Date fictive. Nu este o ofertă comercială Tech-Con.")
        with c2:
            st.markdown("##### Newsletter: automatizare pentru fabrici")
            with st.form("newsletter", clear_on_submit=True, border=False):
                email = st.text_input("E-mail de test", placeholder="test@exemplu.ro")
                topic = st.selectbox("Subiect", ["Studii de caz", "Ghiduri tehnice", "Finanțări și granturi"])
                ok = st.checkbox("Confirm că adresa este fictivă (date de test)")
                sent = st.form_submit_button("Abonează-mă", type="primary", use_container_width=True)
            if sent:
                if not EMAIL_RE.match(email.strip()):
                    st.error("Introduceți o adresă de e-mail validă (fictivă).")
                elif not ok:
                    st.error("Bifați confirmarea că adresa este fictivă.")
                elif database.add_subscriber(email, topic):
                    st.success(f"Abonare înregistrată. Abonați în demo: {database.count_subscribers()}.")
                else:
                    st.info("Această adresă este deja abonată.")
