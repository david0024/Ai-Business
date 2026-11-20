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

## Module
| Fișier | Rol |
|---|---|
| `app.py` | UI Streamlit: banner, carduri, animație, preseturi, formular, raport, chat (bara laterală), tab CRM |
| `calculator.py` | Validare, formule, verdict semafor, scor, riscuri, mapare județ → hub Tech-Con |
| `robot_animation.py` | Animație HTML5 Canvas self-contained (fără CDN) |
| `ai_consultant.py` | Client OpenRouter + parser determinist de rezervă |
| `report_builder.py` | Raport Markdown + HTML printabil (`@media print`) |
| `database.py` | SQLite `app.db`, auto-creat, 3 cereri demo pre-încărcate |
