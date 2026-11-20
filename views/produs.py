"""Product & motivation page."""
import pandas as pd
import streamlit as st

import ui


def render() -> None:
    ui.banner()
    st.markdown('<div class="pc-eyebrow">De ce acum · Produsul</div>', unsafe_allow_html=True)
    st.title("Paletizarea găleților nu mai poate depinde de brațele oamenilor")
    st.markdown(
        "Fabricile alimentare din România cresc, dar găsesc tot mai greu oameni pentru munca grea și repetitivă. "
        "La PURATOS, doi operatori pe schimb ridicau găleți de 13 kg de **3 ori pe minut fiecare**. "
        "Celula UR20 preia exact această sarcină, iar oamenii rămân la schimbarea paleților, control și calitate."
    )

    st.subheader("Contextul pieței în 2026")
    st.markdown(
        """
<div class="pc-stats">
 <div class="pc-stat"><div class="v">~200.000</div><div class="l">angajați în industria alimentară, peste 30 mld. € cifră de afaceri (Romalimenta, apr. 2026)</div></div>
 <div class="pc-stat"><div class="v">+2,1%</div><div class="l">producție alimentară în S1 2026, în timp ce industria totală a scăzut cu 3,7% în 9 luni (INS)</div></div>
 <div class="pc-stat"><div class="v">90.000</div><div class="l">contingent de muncitori străini în 2026, față de 150.000 ceruți de patronate</div></div>
 <div class="pc-stat"><div class="v">4.373 lei</div><div class="l">salariu net mediu în industria alimentară, față de 5.843 lei media națională (INS, apr. 2026)</div></div>
 <div class="pc-stat"><div class="v">231</div><div class="l">roboți la 10.000 de angajați, media UE. România nu apare încă în datele IFR</div></div>
 <div class="pc-stat"><div class="v">200k–3 mil. €</div><div class="l">granturi pentru IMM-uri inovatoare în AI și robotică, apel deschis din mai 2026</div></div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.info("Semnal de piață: pe 12 noiembrie 2026, PURATOS a anunțat o fabrică nouă de peste 15 mil. € la Tunari, "
            "cu capacitate +50% și încă doi coboți pentru paletizare. Sursa publică nu precizează furnizorul sau modelul.")

    st.subheader("Cum funcționează celula")
    st.markdown(
        "**Transportor de alimentare → cameră SICK 2D care citește poziția mânerului → braț UR20 cu gripper pneumatic "
        "personalizat → 2 poziții de paletizare pe europaleți.** Cât timp robotul umple un palet, operatorul îl schimbă "
        "pe celălalt. Trei scanere de siguranță reduc viteza sau opresc robotul când cineva intră în zonă."
    )

    a, b = st.columns(2)
    with a:
        st.markdown('<span class="pc-tag fact">Rezultate de test PURATOS — nu reprezintă garanții universale</span>',
                    unsafe_allow_html=True)
        st.table(pd.DataFrame([
            ("Găleți 13 kg", "7,4 găleți/min (+23% față de țintă)", "44 / palet"),
            ("Găleți 5 kg", "8,6 găleți/min (+43% față de țintă)", "100 / palet"),
            ("Țintă client", "minimum 6 găleți/min", "2 poziții / celulă"),
            ("FAT", "fără preluări nereușite observate", "livrare ~4 luni"),
        ], columns=["Format", "Ritm testat", "Detalii"]))
    with b:
        st.markdown('<span class="pc-tag est">Specificații UR20 (Universal Robots)</span>', unsafe_allow_html=True)
        st.table(pd.DataFrame([
            ("Sarcină utilă", "20 kg (include gripperul)"),
            ("Rază de acțiune", "1.750 mm"),
            ("Repetabilitate", "± 0,05 mm"),
            ("Greutate braț", "64 kg"),
            ("Articulații", "6, cu senzori de forță pentru lucru colaborativ"),
            ("Protecție", "IP65"),
        ], columns=["Parametru", "Valoare"]))

    st.subheader("Ce câștigă fabrica")
    c = st.columns(3)
    for col, (t, d) in zip(c, [
        ("Mai puțin efort", "~37 t ridicate manual pe schimb la 6 găleți/min de 13 kg. Peste 4 ori mai mult decât "
                            "cazul public L'Oréal Pune (~8,5 t), care a justificat acolo coboții."),
        ("Ritm măsurabil", "Ritmul celulei se compară direct cu alimentarea liniei. Dacă linia e mai lentă, blocajul "
                           "e în amonte, iar un robot mai rapid nu crește debitul."),
        ("Paleți constanți", "Fiecare palet urmează același model programat, deci stive stabile și mai puține "
                             "re-paletizări."),
    ]):
        col.markdown(f'<div class="pc-card"><h4>{t}</h4><p>{d}</p></div>', unsafe_allow_html=True)

    st.subheader("Limite clare")
    st.markdown(
        "- Sarcina totală (găleată + gripper ~5 kg) trebuie să rămână sub 20 kg, deci găleți de maximum ~15 kg.\n"
        "- Industriile non-alimentare și cerințele de spălare se validează separat.\n"
        "- **În afara ofertei:** transport autonom MiR (AGV/AMR), înfoliere, expediere.\n"
        "- Nu calculăm economii salariale sau ROI personalizat. Afișăm doar fereastra orientativă de 18–40 luni."
    )
    st.caption("Surse: studiul de caz Tech-Con/PURATOS, INS, Romalimenta, IFR, Universal Robots, presa economică 2026 "
               "(revistabiz, ZF, Agerpres). Cifrele de afaceri ale firmelor sunt pe 2025, ultimele bilanțuri depuse.")
    with st.container(key="cta"):
        st.page_link(st.session_state.pages["evaluare"], label="Evaluați linia dvs.", icon=":material/arrow_forward:")
    ui.chat_widget()
    ui.footer()
