"""SEO / AI-search helpers: FAQ content, JSON-LD structured data."""
import json

import streamlit as st

APP_URL = "https://ai-business-gaxjny2cz9duwfeeogktjl.streamlit.app/"
DESCRIPTION = ("PaletCheck UR20 verifică în 2 minute dacă o linie de găleți de 5–15 kg se potrivește pentru o celulă "
               "de paletizare cu robotul colaborativ Universal Robots UR20, ca cea implementată de Tech-Con la PURATOS.")

FAQ = [
    ("Ce face celula de paletizare UR20?",
     "Robotul colaborativ UR20 preia gălețile de pe transportor, iar o cameră SICK 2D verifică poziția mânerului. "
     "Gălețile sunt așezate pe una dintre cele 2 poziții de paletizare, după un model programat. "
     "Sursa: studiul de caz Tech-Con / PURATOS."),
    ("Cât de repede paletizează robotul UR20 gălețile?",
     "În testele PURATOS: 7,4 găleți/min pentru găleți de 13 kg și 8,6 găleți/min pentru găleți de 5 kg, față de "
     "ținta de 6 găleți/min. Sunt rezultate de test, nu garanții pentru orice fabrică."),
    ("Ce greutate maximă poate avea găleata?",
     "UR20 are o sarcină utilă de 20 kg, iar gripperul intră în acest total. Cu un gripper de aproximativ 5 kg "
     "(ipoteză), găleata poate avea cel mult ~15 kg. Sursa: fișa tehnică Universal Robots UR20."),
    ("Ce rămâne de făcut manual?",
     "Schimbarea paleților plini și așezarea separatoarelor între straturi. Transportul autonom MiR, înfolierea și "
     "expedierea nu sunt incluse."),
    ("Cât costă și în cât timp se livrează o celulă?",
     "În scenariul de lucru, o celulă costă 130.000 EUR fără TVA și se livrează în aproximativ 4 luni. Fereastra "
     "orientativă de recuperare este de 18–40 de luni, în funcție de numărul de schimburi."),
    ("Un robot mai rapid crește producția fabricii?",
     "Nu automat. Dacă linia livrează mai puțin decât ritmul robotului, blocajul este în amonte (umplere, "
     "transportor). PaletCheck compară ritmul liniei cu ritmul testat ca să arate unde este limita."),
    ("Pentru ce fabrici se potrivește?",
     "Fabrici alimentare din România care ambalează în găleți de 5–15 kg: ingrediente pentru panificație și "
     "patiserie, lactate în găleți, sosuri pentru HoReCa. Vopselele se potrivesc doar în formate de până la 10 L."),
]


def json_ld() -> str:
    org = {"@type": "Organization", "name": "Tech-Con România",
           "areaServed": "RO", "address": [{"@type": "PostalAddress", "addressLocality": c, "addressCountry": "RO"}
                                          for c in ("Dragomirești-Deal", "Iași", "Timișoara")]}
    product = {"@type": "Product", "name": "Celulă de paletizare găleți cu UR20",
               "description": DESCRIPTION, "brand": {"@type": "Brand", "name": "Universal Robots UR20"},
               "offers": {"@type": "Offer", "price": "130000", "priceCurrency": "EUR",
                          "description": "Preț de scenariu, fără TVA, demo SYSUP 2026"}}
    faq = {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}
    app = {"@type": "WebApplication", "name": "PaletCheck UR20", "url": APP_URL, "inLanguage": "ro",
           "applicationCategory": "BusinessApplication", "description": DESCRIPTION}
    return json.dumps({"@context": "https://schema.org", "@graph": [org, product, app, faq]}, ensure_ascii=False)


def inject_structured_data() -> None:
    """Put JSON-LD and a meta description into the rendered DOM (for crawlers that execute JS)."""
    meta = DESCRIPTION.replace('"', "&quot;")
    html = (f'<script type="application/ld+json">{json_ld()}</script>'
            "<script>(function(){var d=window.parent&&window.parent.document||document;"
            "if(!d.querySelector('meta[name=description]')){var m=d.createElement('meta');m.name='description';"
            f"m.content=\"{meta}\";d.head.appendChild(m);}}}})();</script>")
    try:
        st.html(html, unsafe_allow_javascript=True)
    except TypeError:  # older Streamlit without the flag
        pass


def faq_section() -> None:
    st.markdown("## Întrebări frecvente")
    for q, a in FAQ:
        with st.expander(q):
            st.write(a)
