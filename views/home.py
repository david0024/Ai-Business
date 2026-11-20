"""Landing page."""
import streamlit as st

import calculator as calc
import ui


def render() -> None:
    ui.banner()
    left, right = st.columns([1.05, 1], gap="large", vertical_alignment="center")
    with left:
        st.markdown(
            '<div class="pc-hero"><div class="pc-eyebrow">PaletCheck UR20 · Tech-Con România</div>'
            "<h1>Găleți paletizate de robot.<br><span>Oameni scutiți de 37 de tone pe schimb.</span></h1>"
            '<p class="pc-lead">Celula colaborativă UR20 preia găleți de 5–13 kg de pe linie și le așază pe '
            "2 paleți, la 7,4–8,6 găleți/min în testele PURATOS. Aflați în 2 minute ce câștigă linia dvs.</p></div>",
            unsafe_allow_html=True,
        )
        st.pills("Ramura de producție", calc.SEGMENTS, key="segment_pick",
                 default=st.session_state.segment)
        if st.session_state.get("segment_pick"):
            st.session_state.segment = st.session_state.segment_pick
        with st.container(key="cta"):
            st.page_link(st.session_state.pages["evaluare"], label="Evaluează-ți linia gratuit  →")
    with right:
        ui.robot_arm()

    st.markdown(
        """
<div class="pc-stats">
  <div class="pc-stat"><span class="pc-tag fact">Test PURATOS</span><div class="v">7,4–8,6</div>
    <div class="l">găleți/min la 13 kg și 5 kg (țintă 6). Rezultate de test, nu garanții.</div></div>
  <div class="pc-stat"><span class="pc-tag fact">UR20</span><div class="v">20 kg</div>
    <div class="l">sarcină utilă, cu gripperul inclus. 2 poziții de paletizare, 3 scanere.</div></div>
  <div class="pc-stat"><span class="pc-tag est">Scenariu</span><div class="v">~4 luni</div>
    <div class="l">de la comandă la livrare · 130.000 EUR fără TVA · recuperare orientativă 18–40 luni.</div></div>
</div>
<h3 style="margin-top:1.4rem">Cum funcționează</h3>
<div class="pc-steps">
  <div class="pc-step"><b>1. Alegeți ramura</b><span>Ingrediente, lactate, sosuri sau vopsele ≤ 10 L.</span></div>
  <div class="pc-step"><b>2. Completați 6 date</b><span>Greutate, ritm, schimburi, operatori. Doar date fictive.</span></div>
  <div class="pc-step"><b>3. Primiți raportul</b><span>Timp eliberat, tone neridicate, capacitate și fereastra de recuperare.</span></div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.caption("În afara ofertei: transport autonom MiR (AGV/AMR), înfoliere și expediere. "
               "Schimbarea paleților și separatoarele rămân manuale.")
    ui.chat_widget()
    ui.footer()
