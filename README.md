# Tech-Con UR20 — Pre-Audit & Simulator celulă de paletizare

Aplicație Streamlit (Python + SQLite) care prezintă celula de paletizare UR20 (referință PURATOS),
pre-califică tehnic fabrici prin simulator determinist, afișează o animație interactivă a celulei,
generează Fișa Tehnică de Pre-Fezabilitate și colectează cereri fictive într-un Mini-CRM demo.

> ⚠️ Demo cu date **exclusiv fictive**. Nu introduceți date personale reale sau informații confidențiale.

## Rulare locală
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Consultant AI (opțional)
Fără cheie API, consultantul folosește parserul local determinist (regex/cuvinte-cheie).
Pentru LLM prin OpenRouter, setați în `.streamlit/secrets.toml` sau ca variabile de mediu:
```toml
OPENROUTER_API_KEY = "sk-or-..."
OPENROUTER_MODEL = "anthropic/claude-haiku-4.5"   # opțional
```
Timeout 5 s, răspuns JSON strict; la orice eroare se revine automat la parserul local.
LLM-ul doar extrage parametri — toate calculele (inclusiv conversia tone/schimb → găleți/min) sunt în `calculator.py`.

## Pagini
| Pagină | Conținut |
|---|---|
| Acasă | Landing alb/albastru/negru, braț UR20 animat (SVG), alegerea ramurii, CTA spre evaluare |
| Evaluare | Formular cu 7 câmpuri → raport pe 4 piloni (bani/capacitate, timp, oameni, calitate), descărcare HTML, cerere în CRM |
| Produs | Motivație cu date 2026, fapte PURATOS vs. specificații UR20, limite |
| Resurse | Feed filtrabil: documentație, studii de caz, video, newslettere (linkuri publice) |
| Simulator tehnic & CRM | Pre-auditul detaliat existent + Mini-CRM |

Asistentul (dreapta jos) răspunde din întrebări verificate și preselectează tipul companiei. Footerul are abonare la newsletter (SQLite).

## Module
| Fișier | Rol |
|---|---|
| `app.py` | Navigare între pagini (`st.navigation`) |
| `ui.py` | Temă, banner, braț robotic SVG, asistent flotant, footer cu newsletter |
| `views/` | Paginile; `views/simulator.py` este fostul `app.py` |
| `calculator.py` | Validare, formule, verdict semafor, scor, riscuri, mapare județ → hub Tech-Con |
| `robot_animation.py` | Animație HTML5 Canvas self-contained (fără CDN) |
| `ai_consultant.py` | Client OpenRouter + parser determinist de rezervă |
| `report_builder.py` | Raport Markdown + HTML printabil (`@media print`) |
| `database.py` | SQLite `app.db`, auto-creat, 3 cereri demo pre-încărcate |
