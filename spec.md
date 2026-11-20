# Specificație: Tech-Con UR20 Palletizing Cell Pre-Qualification & Interactive Simulator

Rezumat al cerințelor implementate (vezi README.md pentru module):

- UI integral în limba română; cod în engleză. Python + Streamlit + SQLite; `requirements.txt` fără versiuni fixate.
- Banner permanent: doar date fictive. Zero controale inactive.
- În afara scopului: transport autonom MiR (AGV/AMR), înfoliere, expediere.
- Fără economii salariale / ROI personalizat — doar fereastra 18–40 luni (3 schimburi: 18–24, 2: 24–32, 1: 34–40) și prețul scenariului 130.000 EUR fără TVA.
- Separare strictă: „Rezultate de test PURATOS — nu reprezintă garanții universale” vs. „Estimare bazată pe ipotezele introducerii”.
- Toate calculele în `calculator.py` (zero matematică în LLM):
  - `payload_total = găleată + gripper` vs. 20 kg; `marjă = 20 − payload_total`
  - `reper = 8,6` dacă găleată ≤ 8 kg, altfel `7,4`; `grad_încărcare = debit / reper × 100`
  - gâtuire dacă `debit > 8,6` → recomandare 2 celule în paralel
  - `timp_umplere_palet = nr_găleți / debit`; `timp_separator = (nr_găleți / nr_straturi) / debit`
  - ROȘU dacă payload > 20 kg; GALBEN dacă debit > reper, non-alimentar, aer ≠ Da, lichid, marjă < 1,5 kg, câmpuri confidențiale sau riscuri specifice; altfel VERDE
- Hub-uri: Dragomirești-Deal (Sud), Iași (Moldova + Harghita), Timișoara (Vest / Nord-Vest).
- 3 preseturi (Verde / Galben confidențial / Roșu suprasarcină), validare blocantă pentru valori ≤ 0.
- Export HTML printabil + Markdown/TXT; Mini-CRM SQLite cu filtre Hub/Verdict și KPI.
- Consultant AI: auto-completare din limbaj natural, Q&A pe brief-ul PURATOS, extragere riscuri nestructurate; contract JSON strict.
