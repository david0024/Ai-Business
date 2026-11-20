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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root {{ --blue:{BLUE}; --ink:{INK}; --muted:#5B6475; --line:#E6EAF0; --soft:#F6F8FB; }}
html, body, .stApp, .stMarkdown p, .stMarkdown li, h1, h2, h3, h4, h5, label, input, textarea, select,
button p, [data-testid="stWidgetLabel"] p {{ font-family:'Inter', system-ui, -apple-system, sans-serif; }}
/* hide Streamlit chrome (toolbar, anchors, footer badge) */
[data-testid="stToolbarActions"], [data-testid="stAppDeployButton"], [data-testid="stMainMenu"],
[data-testid="stToolbar"] > *:not([data-testid="stTopNav"]):not(:has([data-testid="stTopNav"])),
[data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stHeaderActionElements"], .stDeployButton, footer {{ display:none !important; }}
.block-container {{ padding-top:0; padding-bottom:2rem; max-width:1120px; }}
h1,h2,h3 {{ color:var(--ink); letter-spacing:-0.025em; font-weight:700; }}
.pc-note {{ display:flex; gap:8px; align-items:center; color:var(--muted); font-size:.8rem; margin-bottom:1.4rem; }}
.pc-note svg {{ flex:none; }}
.pc-eyebrow {{ display:inline-flex; align-items:center; gap:8px; color:var(--blue); font-weight:600; font-size:.78rem;
  letter-spacing:.06em; text-transform:uppercase; }}
.pc-eyebrow:before {{ content:""; width:18px; height:2px; background:var(--blue); }}
.pc-hero h1 {{ color:var(--ink) !important; font-size:clamp(2.1rem, 4.6vw, 3.4rem); line-height:1.05; font-weight:700;
  letter-spacing:-0.035em; margin:.6rem 0 1rem; padding:0; }}
.pc-hero h1 .mu {{ color:var(--muted); font-style:normal; }}
.pc-lead {{ font-size:1.1rem; color:var(--muted); line-height:1.6; max-width:33rem; }}
.pc-stats {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:0; margin:2rem 0 1rem;
  border:1px solid var(--line); border-radius:16px; overflow:hidden; }}
.pc-stat {{ padding:18px 20px; background:#fff; border-right:1px solid var(--line); }}
.pc-stat:last-child {{ border-right:none; }}
.pc-stat .v {{ font-size:1.65rem; font-weight:700; color:var(--ink); letter-spacing:-0.02em; font-variant-numeric:tabular-nums; }}
.pc-stat .l {{ font-size:.82rem; color:var(--muted); line-height:1.45; margin-top:2px; }}
.pc-card {{ border:1px solid var(--line); border-radius:16px; padding:20px; background:#fff; height:100%;
  box-shadow:0 1px 2px rgba(10,15,28,.04); }}
.pc-card h4 {{ margin:0 0 .4rem; padding:0; font-size:1rem; font-weight:600; }}
.pc-card .big {{ font-size:1.75rem; font-weight:700; color:var(--ink); letter-spacing:-0.02em; line-height:1.1; }}
.pc-card p, .pc-card li {{ color:var(--muted); font-size:.9rem; line-height:1.5; }}
.pc-tag {{ display:inline-block; font-size:.68rem; font-weight:600; border-radius:6px; padding:2px 8px; margin-bottom:8px;
  letter-spacing:.03em; text-transform:uppercase; }}
.pc-tag.fact {{ background:#EAF0FF; color:#0B3FB0; }}
.pc-tag.est {{ background:#F1F3F6; color:#3A404B; }}
.pc-steps {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:24px; }}
.pc-step {{ padding:4px 0; }}
.pc-step .n {{ font-size:.75rem; font-weight:600; color:var(--blue); font-variant-numeric:tabular-nums; }}
.pc-step b {{ display:block; margin:4px 0 2px; font-weight:600; }}
.pc-step span {{ color:var(--muted); font-size:.9rem; line-height:1.5; }}
.st-key-pc_footer {{ border-top:1px solid var(--line); padding:28px 0 8px; margin-top:3rem; }}
.pc-feed {{ border:1px solid var(--line); border-radius:14px; padding:16px 18px; margin-bottom:10px; background:#fff; }}
.pc-feed .t {{ font-weight:600; color:var(--ink); }}
.pc-feed .m {{ font-size:.72rem; color:var(--muted); font-weight:600; text-transform:uppercase; letter-spacing:.06em; }}
.pc-feed p {{ margin:.25rem 0 .35rem; color:var(--muted); font-size:.9rem; }}
.pc-feed a {{ color:var(--blue); font-weight:600; text-decoration:none; }}
.stButton button, .stFormSubmitButton button, .stDownloadButton button, [data-testid="stPopover"] button {{ border-radius:10px; font-weight:600; }}
.st-key-cta a {{ background:var(--ink); color:#fff !important; border-radius:10px; padding:.75rem 1.3rem; justify-content:center;
  transition:background .2s ease; }}
.st-key-cta a:hover {{ background:var(--blue); }}
.st-key-cta a p {{ color:#fff !important; font-weight:600; font-size:1rem; }}
.st-key-cta a span {{ color:#fff !important; }}
/* custom navbar (Streamlit header hidden) */
header[data-testid="stHeader"] {{ display:none !important; }}
.st-key-pc_nav {{ position:sticky; top:0; z-index:999; background:rgba(255,255,255,.9); backdrop-filter:saturate(180%) blur(12px);
  border-bottom:1px solid var(--line); padding:10px 0; margin-bottom:.6rem; }}
.pc-brand {{ font-weight:700; font-size:1.02rem; letter-spacing:-0.02em; color:var(--ink); white-space:nowrap; }}
.pc-brand span {{ color:var(--blue); }}
.st-key-pc_navlinks {{ gap:6px !important; justify-content:center; }}
.st-key-pc_navlinks [data-testid="stPageLink"] a {{ padding:.5rem .95rem; border-radius:8px; transition:background .15s ease, color .15s ease; }}
.st-key-pc_navlinks [data-testid="stPageLink"] a:hover {{ background:var(--soft); }}
.st-key-pc_navlinks [data-testid="stPageLink"] a p {{ font-weight:500; font-size:.95rem; color:var(--ink); }}
.st-key-pc_navlinks [data-testid="stPageLink"] a:hover p {{ color:var(--blue); text-decoration:underline; text-underline-offset:4px; }}
.st-key-pc_navcta a {{ background:var(--blue); border-radius:10px; padding:.55rem 1.1rem; justify-content:center; }}
.st-key-pc_navcta a:hover {{ background:var(--ink); }}
.st-key-pc_navcta a p, .st-key-pc_navcta a span {{ color:#fff !important; font-weight:600; white-space:nowrap; }}
/* auto-scrolling segment chips */
.st-key-seg_marquee {{ overflow:hidden; mask-image:linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent);
  -webkit-mask-image:linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent); }}
.st-key-seg_track {{ width:max-content !important; flex-wrap:nowrap !important; gap:8px !important;
  animation:pcMarquee 22s linear infinite; }}
.st-key-seg_marquee:hover .st-key-seg_track {{ animation-play-state:paused; }}
.st-key-seg_track button {{ border-radius:999px; white-space:nowrap; font-weight:500; }}
@keyframes pcMarquee {{ from {{ transform:translateX(0); }} to {{ transform:translateX(-50%); }} }}
@media (prefers-reduced-motion: reduce) {{ .st-key-seg_track {{ animation:none; }} .st-key-seg_marquee {{ overflow-x:auto; }} }}
.pc-seg-label {{ font-size:.85rem; color:var(--muted); margin:.4rem 0 .2rem; }}
.pc-seg-label b {{ color:var(--ink); font-weight:600; }}
@media (max-width: 640px) {{
  .st-key-pc_navlinks {{ overflow-x:auto; flex-wrap:nowrap !important; justify-content:flex-start; }}
  .st-key-pc_navlinks [data-testid="stPageLink"] a {{ padding:.45rem .6rem; }}
  .pc-brand, .st-key-pc_navcta, .st-key-pc_nav [data-testid="stElementContainer"]:has(.pc-brand) {{ display:none; }}
  .st-key-pc_navlinks {{ flex:1 1 auto; width:100% !important; }}
}}
/* Floating assistant, bottom-right */
.st-key-pc_chat {{ position:fixed; right:20px; bottom:20px; z-index:9999; width:auto !important; }}
.st-key-pc_chat button {{ background:var(--ink); color:#fff; border:none; border-radius:999px; padding:.7rem 1.15rem;
  box-shadow:0 12px 32px rgba(10,15,28,.25); }}
.st-key-pc_chat button:hover {{ background:var(--blue); color:#fff; }}
@media (max-width: 640px) {{
  .pc-stats {{ grid-template-columns:1fr; }}
  .pc-stat {{ border-right:none; border-bottom:1px solid var(--line); }}
  .pc-steps {{ grid-template-columns:1fr; gap:14px; }}
  .st-key-pc_chat {{ right:12px; bottom:12px; }}
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
        '<div class="pc-note"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0B5FFF" '
        'stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v5M12 16h.01"/></svg>'
        "<span>Prototip demonstrativ: folosiți doar date fictive, fără date personale sau informații "
        "confidențiale ale companiei.</span></div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Robot arm: pure SVG + CSS, only the arm moves up and down.
# --------------------------------------------------------------------------
ROBOT_ARM_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 460 400" role="img" aria-label="Braț robotic colaborativ UR20">
<style>
.upper, .fore, .wrist, .shadow {{ animation-duration:5.6s; animation-iteration-count:infinite;
  animation-timing-function:cubic-bezier(.65,0,.35,1); }}
.upper {{ transform-box:view-box; transform-origin:140px 268px; animation-name:a1; }}
.fore  {{ transform-box:view-box; transform-origin:262px 136px; animation-name:a2; }}
.wrist {{ transform-box:view-box; transform-origin:372px 168px; animation-name:a3; }}
.shadow {{ transform-box:fill-box; transform-origin:center; animation-name:a4; }}
.led {{ animation:led 2.8s ease-in-out infinite; }}
@keyframes a1 {{ 0%,12% {{ transform:rotate(-6deg); }} 46%,62% {{ transform:rotate(5deg); }} 100% {{ transform:rotate(-6deg); }} }}
@keyframes a2 {{ 0%,12% {{ transform:rotate(-8deg); }} 46%,62% {{ transform:rotate(12deg); }} 100% {{ transform:rotate(-8deg); }} }}
@keyframes a3 {{ 0%,12% {{ transform:rotate(14deg); }} 46%,62% {{ transform:rotate(-17deg); }} 100% {{ transform:rotate(14deg); }} }}
@keyframes a4 {{ 0%,12% {{ transform:scaleX(.82); opacity:.10; }} 46%,62% {{ transform:scaleX(1.05); opacity:.2; }} 100% {{ transform:scaleX(.82); opacity:.10; }} }}
@keyframes led {{ 0%,100% {{ opacity:.35; }} 50% {{ opacity:1; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation:none !important; }} }}
</style>
<defs>
  <radialGradient id="bg" cx="70%" cy="35%" r="80%"><stop offset="0" stop-color="#EEF3FF"/><stop offset="1" stop-color="#FFFFFF"/></radialGradient>
  <linearGradient id="alu" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#FFFFFF"/><stop offset=".45" stop-color="#EEF1F5"/><stop offset="1" stop-color="#C3CBD6"/></linearGradient>
  <linearGradient id="joint" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#F7F9FB"/><stop offset="1" stop-color="#B9C2CE"/></linearGradient>
  <linearGradient id="cap" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#3A4252"/><stop offset="1" stop-color="#0E131C"/></linearGradient>
  <linearGradient id="graphite" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#1A202B"/><stop offset=".5" stop-color="#363E4C"/><stop offset="1" stop-color="#0E131C"/></linearGradient>
  <filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="6" stdDeviation="7" flood-color="#0A0F1C" flood-opacity=".14"/></filter>
</defs>
<rect width="460" height="400" rx="24" fill="url(#bg)"/>
<g stroke="#E3E8F0" stroke-width="1">
  <path d="M0 356 H460"/><path d="M40 356 L0 400 M120 356 L100 400 M200 356 L200 400 M280 356 L300 400 M360 356 L400 400 M440 356 L460 380"/>
</g>
<ellipse class="shadow" cx="372" cy="356" rx="62" ry="7" fill="{INK}"/>
<ellipse cx="140" cy="356" rx="66" ry="7" fill="{INK}" opacity=".12"/>
<!-- pedestal -->
<rect x="96" y="300" width="88" height="54" rx="6" fill="url(#graphite)"/>
<rect x="86" y="346" width="108" height="10" rx="3" fill="{INK}"/>
<circle class="led" cx="170" cy="314" r="3" fill="{BLUE}"/>
<rect x="110" y="272" width="60" height="32" rx="8" fill="url(#joint)" stroke="#AEB8C5"/>
<rect x="110" y="292" width="60" height="4" fill="{BLUE}"/>
<g filter="url(#soft)">
 <g class="upper">
  <path d="M126 252 L248 120 L276 152 L154 284 Z" fill="url(#alu)" stroke="#B4BDC9" stroke-width="1"/>
  <path d="M131 256 L251 127" stroke="#FFFFFF" stroke-width="3" opacity=".9"/>
  <circle cx="140" cy="268" r="31" fill="url(#joint)" stroke="#AEB8C5"/>
  <circle cx="140" cy="268" r="22" fill="none" stroke="{BLUE}" stroke-width="3.5"/>
  <circle cx="140" cy="268" r="16" fill="url(#cap)"/>
  <circle cx="134" cy="262" r="4" fill="#FFFFFF" opacity=".25"/>
  <g class="fore">
   <path d="M258 122 L376 152 L368 184 L250 154 Z" fill="url(#alu)" stroke="#B4BDC9" stroke-width="1"/>
   <path d="M262 126 L376 155" stroke="#FFFFFF" stroke-width="2.5" opacity=".9"/>
   <circle cx="262" cy="136" r="26" fill="url(#joint)" stroke="#AEB8C5"/>
   <circle cx="262" cy="136" r="18" fill="none" stroke="{BLUE}" stroke-width="3"/>
   <circle cx="262" cy="136" r="13" fill="url(#cap)"/>
   <circle cx="257" cy="131" r="3.5" fill="#FFFFFF" opacity=".25"/>
   <g class="wrist">
    <circle cx="372" cy="168" r="19" fill="url(#joint)" stroke="#AEB8C5"/>
    <circle cx="372" cy="168" r="13" fill="none" stroke="{BLUE}" stroke-width="2.5"/>
    <circle cx="372" cy="168" r="9" fill="url(#cap)"/>
    <rect x="361" y="184" width="22" height="24" rx="5" fill="url(#joint)" stroke="#AEB8C5"/>
    <rect x="361" y="196" width="22" height="3" fill="{BLUE}"/>
    <!-- gripper -->
    <rect x="336" y="208" width="72" height="10" rx="3" fill="url(#cap)"/>
    <rect x="339" y="216" width="8" height="30" rx="2" fill="#2A313D"/>
    <rect x="397" y="216" width="8" height="30" rx="2" fill="#2A313D"/>
    <!-- bucket -->
    <path d="M348 240 h48 l-5 54 a4 4 0 0 1 -4 3.5 h-30 a4 4 0 0 1 -4 -3.5 z" fill="#FFFFFF" stroke="#C3CBD6" stroke-width="1.5"/>
    <rect x="345" y="234" width="54" height="8" rx="2" fill="#FFFFFF" stroke="#C3CBD6" stroke-width="1.5"/>
    <path d="M354 254 h36" stroke="#E6EAF0" stroke-width="6"/>
   </g>
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
        with st.popover("Asistent UR20", icon=":material/forum:"):
            st.markdown("**Asistent PaletCheck** · răspunsuri verificate din studiul de caz")
            st.pills("Tipul companiei", calc.SEGMENTS, key="pc_chat_segment", on_change=_on_segment_pick)
            box = st.container(height=240)
            with box:
                if not ss.pc_chat:
                    st.caption("Alegeți tipul companiei sau puneți o întrebare. Calculele sunt făcute în Python, nu de AI.")
                for role, msg in ss.pc_chat[-8:]:
                    st.chat_message(role, avatar=":material/person:" if role == "user" else ":material/precision_manufacturing:").write(msg)
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


# --------------------------------------------------------------------------
# Navbar with CTA on the right, and auto-scrolling segment chips
# --------------------------------------------------------------------------
NAV_KEYS = ["home", "evaluare", "produs", "resurse", "simulator"]
NAV_LABELS = {"home": "Acasă", "evaluare": "Evaluare", "produs": "Produs", "resurse": "Resurse", "simulator": "Simulator & CRM"}


def navbar(pages: dict) -> None:
    with st.container(key="pc_nav", horizontal=True, vertical_alignment="center", gap="medium"):
        st.markdown('<div class="pc-brand">PaletCheck <span>UR20</span></div>', unsafe_allow_html=True, width="content")
        with st.container(key="pc_navlinks", horizontal=True, vertical_alignment="center"):
            for k in NAV_KEYS:
                st.page_link(pages[k], label=NAV_LABELS[k], width="content")
        with st.container(key="pc_navcta", width="content"):
            st.page_link(pages["evaluare"], label="Evaluează-ți linia", icon=":material/arrow_forward:", width="content")


def _pick_segment(seg: str) -> None:
    st.session_state.segment = seg


def segment_marquee() -> None:
    current = st.session_state.segment
    st.markdown(f'<div class="pc-seg-label">Ramura de producție: <b>{current}</b></div>', unsafe_allow_html=True)
    with st.container(key="seg_marquee"):
        with st.container(key="seg_track", horizontal=True):
            for copy in range(2):  # two copies make the loop seamless
                for i, seg in enumerate(calc.SEGMENTS):
                    st.button(seg, key=f"seg_{copy}_{i}", on_click=_pick_segment, args=(seg,),
                              type="primary" if seg == current else "secondary", width="content")
