"""Resources feed: documentation, case studies, videos, newsletters (public links)."""
import streamlit as st

import ui

RESOURCES = [
    ("Documentație", "Universal Robots", "UR20: pagina oficială a produsului",
     "Specificații, sarcină de 20 kg, rază de 1.750 mm și aplicații de paletizare.",
     "https://www.universal-robots.com/products/ur20/"),
    ("Documentație", "Universal Robots", "UR20: descrierea demo-ului (PDF)",
     "Fișa demonstrativă a UR20, utilă pentru discuția tehnică.",
     "https://www.universal-robots.com/media/1824575/ur20-demo-description.pdf"),
    ("Studiu de caz", "Universal Robots", "Bob's Red Mill: paletizare cu UR20",
     "Producător alimentar care a introdus paletizarea cu UR20 la final de linie.",
     "https://www.universal-robots.com/case-stories/bobs-red-mill/"),
    ("Studiu de caz", "Universal Robots", "Raumland: UR20 paletizează cutii de vin",
     "Exemplu de celulă UR20 la final de linie într-o fabrică mică din Germania.",
     "https://universal-robots.com/case-stories/raumland-gmbh"),
    ("Video", "Universal Robots", "Video: UR20 la Bob's Red Mill",
     "Cum arată în producție o celulă de paletizare cu UR20.",
     "https://www.universal-robots.com/resources/videos/ur20-cobot-enables-new-palletizing-opportunity-at-bob-s-red-mill/"),
    ("Video", "Universal Robots", "Video: lansarea UR20 (Automatica)",
     "Prezentarea oficială a brațului UR20.",
     "https://video.universal-robots.com/automatica-ur20-announcement"),
    ("Video", "Automation World", "Video: sistem de paletizare UR + Robotiq",
     "Demonstrație a unei celule colaborative de paletizare.",
     "https://www.automationworld.com/factory/robotics/video/33013410/universal-robots-and-robotiq-palletizing-system"),
    ("Siguranță", "EU-OSHA", "Checklist pentru riscurile manipulării manuale",
     "Lista oficială EU-OSHA pentru evaluarea ridicării manuale a greutăților.",
     "https://osha.europa.eu/en/publications/e-facts/efact44/view"),
    ("Piață", "IFR", "Densitatea roboților crește în Europa (2026)",
     "Comunicatul IFR despre roboții la 10.000 de angajați.",
     "https://ifr.org/ifr-press-releases/news/robot-density-surges-in-europe-asia-and-americas"),
    ("Piață", "IFR", "World Robotics 2025: cererea de roboți s-a dublat în 10 ani",
     "Raportul anual al Federației Internaționale de Robotică.",
     "https://ifr.org/ifr-press-releases/global-robot-demand-in-factories-doubles-over-10-years"),
    ("Newsletter", "The Robot Report", "The Robot Report: newsletter",
     "Știri săptămânale despre robotică industrială și automatizare.",
     "https://www.therobotreport.com/the-robot-report-enewsletter/"),
    ("Newsletter", "Robotics 24/7", "Robotics 24/7: newslettere",
     "Noutăți despre roboți în logistică și producție.",
     "https://robotics247.com/site/newsletters"),
]


def render() -> None:
    ui.banner()
    st.markdown('<div class="pc-eyebrow">Resurse</div>', unsafe_allow_html=True)
    st.title("Documentație, video și noutăți")
    types = sorted({r[0] for r in RESOURCES})
    c1, c2 = st.columns([2, 1])
    q = c1.text_input("Caută", placeholder="Ex.: video, paletizare, siguranță")
    pick = c2.multiselect("Tip", types)
    items = [r for r in RESOURCES
             if (not pick or r[0] in pick)
             and (not q or q.lower() in " ".join(r).lower())]
    st.caption(f"{len(items)} resurse · linkuri publice externe, se deschid într-o filă nouă")
    for kind, src, title, desc, url in items:
        st.markdown(
            f'<div class="pc-feed"><div class="m">{kind} · {src}</div><div class="t">{title}</div>'
            f'<p>{desc}</p><a href="{url}" target="_blank" rel="noopener">Deschide →</a></div>',
            unsafe_allow_html=True,
        )
    if not items:
        st.info("Nicio resursă nu se potrivește căutării.")
    ui.footer()
