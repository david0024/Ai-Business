# Specificație: Tech-Con UR20 Palletizing Cell Pre-Qualification & Interactive Simulator

Rezumat al cerințelor implementate (vezi README.md pentru module):

- UI integral în limba română; cod în engleză. Python + Streamlit + SQLite; `requirements.txt` fără versiuni fixate.
- Banner permanent: doar date fictive. Zero controale inactive.
- În afara scopului: transport autonom MiR (AGV/AMR), înfoliere, expediere.
- Fără economii salariale / ROI personalizat — doar fereastra 18–40 luni (3 schimburi: 18–24, 2: 24–32, 1: 34–40) și prețul scenariului 130.000 EUR fără TVA.
- Separare strictă: „Rezultate de test PURATOS — nu reprezintă garanții universale” vs. „Estimare bazată pe ipotezele introducerii”.
- Toate calculele în `calculator.py` (zero matematică în LLM):
  - `payload_total = găleată + gripper` vs. 20 kg; `marjă = 20 − payload_total`
  - `reper = 8,6` dacă găleată ≤ 5 kg (singurul format testat la 8,6), altfel `7,4`; `grad_încărcare = debit / reper × 100`
  - gâtuire dacă `debit > 8,6` → recomandare 2 celule în paralel
  - `ritm_efectiv = min(debit, reper)`; `timp_umplere_palet = nr_găleți / ritm_efectiv`; `timp_separator = (nr_găleți / nr_straturi) / ritm_efectiv`
  - `tone_manual_schimb = debit × 60 × 8 h × greutate / 1000` (ipoteză 8 h, 2 operatori)
  - gripper implicit 5 kg (ipoteză, aceeași ca în modelul financiar)
  - ROȘU dacă payload > 20 kg; GALBEN dacă debit > reper, non-alimentar, aer ≠ Da, lichid, marjă < 1,5 kg, câmpuri confidențiale sau riscuri specifice; altfel VERDE
- Hub-uri: Dragomirești-Deal (Sud), Iași (Moldova + Harghita), Timișoara (Vest / Nord-Vest).
- 4 preseturi (Verde / Galben confidențial / Roșu suprasarcină / Date lipsă sau greșite), validare blocantă pentru valori ≤ 0.
- Export HTML printabil + Markdown/TXT; Mini-CRM SQLite cu filtre Hub/Verdict și KPI.
- Consultant AI: auto-completare din limbaj natural, Q&A pe brief-ul PURATOS, extragere riscuri nestructurate; contract JSON strict.
