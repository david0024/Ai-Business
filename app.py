"""PaletCheck UR20 — entry point and navigation.

Run locally: streamlit run app.py
UI is Romanian; all calculations live in calculator.py.
"""
import streamlit as st

import ui
from views import evaluare, home, produs, resurse

st.set_page_config(page_title="PaletCheck UR20 · Tech-Con", page_icon=":material/precision_manufacturing:", layout="wide",
                   initial_sidebar_state="collapsed")
ui.setup()

pages = {
    "home": st.Page(home.render, title="Acasă", icon=":material/home:", url_path="acasa", default=True),
    "evaluare": st.Page(evaluare.render, title="Evaluare", icon=":material/fact_check:", url_path="evaluare"),
    "produs": st.Page(produs.render, title="Produs", icon=":material/precision_manufacturing:", url_path="produs"),
    "resurse": st.Page(resurse.render, title="Resurse", icon=":material/library_books:", url_path="resurse"),
    "simulator": st.Page("views/simulator.py", title="Simulator tehnic & CRM", icon=":material/tune:", url_path="simulator"),
}
st.session_state.pages = pages
pg = st.navigation(list(pages.values()), position="hidden")
ui.navbar(pages)
pg.run()
