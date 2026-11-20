"""PaletCheck UR20 — entry point and navigation.

Run locally: streamlit run app.py
UI is Romanian; all calculations live in calculator.py.
"""
import streamlit as st

import ui
from views import evaluare, home, produs, resurse

st.set_page_config(page_icon=":material/precision_manufacturing:", layout="wide",
                   initial_sidebar_state="collapsed")
ui.setup()

pages = {
    "home": st.Page(home.render, title="PaletCheck UR20 · Paletizare automată a găleților cu cobot", icon=":material/home:", url_path="acasa", default=True),
    "evaluare": st.Page(evaluare.render, title="Evaluare gratuită a liniei de găleți · PaletCheck UR20", icon=":material/fact_check:", url_path="evaluare"),
    "produs": st.Page(produs.render, title="Celula de paletizare UR20: date tehnice și piață 2026", icon=":material/precision_manufacturing:", url_path="produs"),
    "resurse": st.Page(resurse.render, title="Resurse despre paletizarea cu coboți UR20", icon=":material/library_books:", url_path="resurse"),
    "simulator": st.Page("views/simulator.py", title="Simulator tehnic UR20 și Mini-CRM", icon=":material/tune:", url_path="simulator"),
}
st.session_state.pages = pages
pg = st.navigation(list(pages.values()), position="hidden")
ui.navbar(pages)
pg.run()
