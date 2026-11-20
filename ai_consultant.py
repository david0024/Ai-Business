"""AI technical consultant: OpenRouter client + deterministic fallback parser.

Contract: every turn returns a dict shaped like
    {
      "reply": str,                      # Romanian
      "form_updates": {...},             # normalised, validated values or None
      "confidential_fields": [str],
      "custom_risks": [str],
      "ready_for_report": bool,
      "source": "llm" | "fallback",
      "calc_note": str | None,           # deterministic calculation shown to the user
    }

The LLM only extracts parameters and phrases answers. Any arithmetic (e.g.
tonnage per shift -> buckets/minute) is done in Python via `calculator`.
"""

from __future__ import annotations

import json
import re

import requests

import calculator as calc

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "anthropic/claude-haiku-4.5"
TIMEOUT_S = 5.0

FORM_KEYS = [
    "industry", "bucket_weight_kg", "gripper_weight_kg", "content_type", "has_handle",
    "line_rate_bpm", "shifts", "side_selection", "region", "air_supply", "pallet_equipment",
]

# --------------------------------------------------------------------------
# Knowledge base (PURATOS brief) used both in the LLM prompt and the fallback
# --------------------------------------------------------------------------
BRIEF = """Celula de paletizare UR20 implementată de Tech-Con România la PURATOS:
- Flux: transportor alimentare → cameră vision 2D SICK (detectare orientare mâner) → braț UR20 + gripper pneumatic personalizat → 2 poziții de paletizare pe europaleți.
- Rezultate de test PURATOS (nu garanții universale): 7,4 găleți/min la 13 kg (44 găleți/palet), 8,6 găleți/min la 5 kg (100 găleți/palet), peste ținta minimă de 6 găleți/min.
- UR20: sarcină maximă 20 kg (găleată + gripper).
- Siguranță: 3 scanere optice de siguranță pe cele 2 poziții; operatorul selectează din panou partea activă de preluare (Stânga/Dreapta), schimbă paleții manual și așază manual separatoarele.
- În afara scopului: transport autonom MiR (AGV/AMR), înfoliere, expediere.
- Livrare orientativă ~4 luni (reper PURATOS); amortizare orientativă 18–40 luni în funcție de schimburi (3 schimburi: 18–24, 2: 24–32, 1: 34–40 luni); preț scenariu 130.000 EUR fără TVA.
- Nu se calculează economii salariale și nici ROI personalizat.
- Hub-uri Tech-Con: Dragomirești-Deal (Sud), Iași (Moldova), Timișoara (Vest/Nord-Vest)."""

SYSTEM_PROMPT = f"""Ești consultantul tehnic Tech-Con pentru celula de paletizare UR20. Răspunzi DOAR în limba română, concis (max. 4 propoziții).
Folosește exclusiv aceste informații:
{BRIEF}

Reguli stricte:
1. NU faci calcule. Dacă utilizatorul dă producția în tone/kg pe schimb sau pe zi, completează "production_kg" (kg), "period" ("schimb" sau "zi") și "shift_hours"; lasă "line_rate_bpm" null. Completează "line_rate_bpm" doar dacă utilizatorul a spus explicit găleți pe minut (sau găleți pe oră → pune valoarea în "line_rate_bph").
2. Nu inventa date. Câmpurile nemenționate rămân null.
3. Riscuri de șantier nemenționate în formular (condens, spațiu strâmt, găleți ovale, temperatură scăzută, mediu umed etc.) → "custom_risks" (texte scurte în română).
4. Informații pe care utilizatorul spune că sunt confidențiale/nu le poate da → "confidential_fields" (ex: "Debit exact linie de vârf", "Nume companie").
5. Dacă lipsește o dată critică (greutate găleată, debit/producție, județ), pune cel mult O întrebare scurtă la finalul răspunsului.
6. Nu calcula economii salariale sau ROI; menționează doar fereastra orientativă 18–40 luni și prețul scenariului.
7. Atenționează utilizatorul să folosească doar date fictive dacă pare să ofere date reale.

Răspunde STRICT cu un obiect JSON valid, fără text în afara lui:
{{
  "reply": "text în română",
  "form_updates": {{
    "industry": "alimentara | non-alimentara | null",
    "bucket_weight_kg": null, "gripper_weight_kg": null,
    "content_type": "lichid | pasta | solid | null",
    "has_handle": null, "line_rate_bpm": null, "line_rate_bph": null,
    "production_kg": null, "period": "schimb | zi | null", "shift_hours": null,
    "shifts": null, "side_selection": "stanga | dreapta | dual | null",
    "region": "numele județului sau orașului | null",
    "air_supply": "da | nu | nu_stiu | null",
    "pallet_equipment": "liza | transpalet | stivuitor | null"
  }},
  "confidential_fields": [],
  "custom_risks": [],
  "ready_for_report": false
}}"""

# --------------------------------------------------------------------------
# Keyword tables (patterns are matched against diacritic-free lowercase text)
# --------------------------------------------------------------------------
FOOD_WORDS = r"\b(iaurt\w*|lactate|lapte|branz\w*|smantan\w*|maionez\w*|ketchup|sos\w*|gem\w*|dulceat\w*|miere|margarin\w*|unt|crem\w* (?:de )?patiser\w*|patiser\w*|panific\w*|alimentar\w*|ciocolat\w*|umplutur\w*|glazur\w*|mustar|ulei comestibil|fructe|legume|muraturi)\b"
NONFOOD_WORDS = r"\b(vopse\w*|lacuri|adeziv\w*|chimic\w*|detergent\w*|lubrifiant\w*|ulei de motor|tencuial\w*|glet\w*|non[- ]?alimentar\w*|cosmetic\w*|chit\w*|amorsa|rasin\w*|ingrasamint\w*|solvent\w*)\b"
LIQUID_WORDS = r"\b(lichid\w*|lapte|sirop\w*|ulei\w*|suc\w*|detergent lichid|apa)\b"
PASTE_WORDS = r"\b(past\w*|iaurt\w*|crem\w*|maionez\w*|smantan\w*|gem\w*|vascos\w*|vopse\w*|glet\w*|tencuial\w*|ketchup|mustar|umplutur\w*|margarin\w*|unt|branz\w*)\b"
SOLID_WORDS = r"\b(pulber\w*|faina|praf\w*|granul\w*|solid\w*|zahar|sare|ciment)\b"

RISK_PATTERNS = [
    (r"\bcondens\w*", "Condens în zona de lucru — aderență gripper și stabilitate găleată de validat"),
    (r"spatiu\w* (?:strampt|stramt|ingust|limitat|mic|redus)|(?:strampt|stramt|ingust)\w*|loc putin|hala (?:mica|ingusta)", "Spațiu strâmt / amprentă la sol limitată — layout celulă și acces paleți de verificat"),
    (r"\boval\w*|dreptunghiular\w*|neregulat\w*", "Găleți cu formă non-cilindrică (ovale/dreptunghiulare) — gripper dedicat și schemă de paletizare specifică"),
    (r"temperatur\w* (?:scazut\w*|joas\w*|negativ\w*)|\bfrig\w*|congel\w*|camer\w* frigorific\w*|-\s?\d+\s?(?:°|grade)", "Temperatură scăzută — comportament pneumatic, condens și componente de validat"),
    (r"\bumed\w*|umiditat\w*|spalar\w*|apa pe jos|wash ?down", "Mediu umed / spălare — grad de protecție IP pentru robot, gripper și senzori"),
    (r"\bpraf\w*|pulverulent\w*", "Mediu cu praf — protecție echipamente și curățenie optică scanere/cameră"),
    (r"capac\w* (?:nesecurizat|slab|desfacut|instabil)|fara capac", "Capac nesecurizat — risc de deschidere la manipulare"),
    (r"deformabil\w*|perete subtire|ambalaj (?:moale|subtire)", "Ambalaj deformabil — forța de prindere a gripperului trebuie validată"),
    (r"\bvibrat\w*", "Vibrații în zona celulei — fixarea robotului și precizia de plasare de verificat"),
    (r"\batex\b|exploziv\w*|inflamabil\w*", "Mediu potențial ATEX / inflamabil — necesită analiză de conformitate separată"),
]

CITY_TO_COUNTY = {
    "bucuresti": "București", "cluj-napoca": "Cluj", "cluj napoca": "Cluj", "timisoara": "Timiș",
    "craiova": "Dolj", "ploiesti": "Prahova", "pitesti": "Argeș", "oradea": "Bihor",
    "targu mures": "Mureș", "tirgu mures": "Mureș", "baia mare": "Maramureș", "constanta": "Constanța",
    "galati": "Galați", "braila": "Brăila", "brasov": "Brașov", "sibiu": "Sibiu", "bacau": "Bacău",
    "suceava": "Suceava", "piatra neamt": "Neamț", "botosani": "Botoșani", "focsani": "Vrancea",
    "ramnicu valcea": "Vâlcea", "rimnicu vilcea": "Vâlcea", "targoviste": "Dâmbovița",
    "targu jiu": "Gorj", "drobeta": "Mehedinți", "deva": "Hunedoara", "alba iulia": "Alba",
    "zalau": "Sălaj", "satu mare": "Satu Mare", "bistrita": "Bistrița-Năsăud", "resita": "Caraș-Severin",
    "slatina": "Olt", "alexandria": "Teleorman", "slobozia": "Ialomița", "miercurea ciuc": "Harghita",
    "sfantu gheorghe": "Covasna", "otopeni": "Ilfov", "voluntari": "Ilfov", "popesti": "Ilfov",
    "chiajna": "Ilfov", "dragomiresti": "Ilfov", "arad": "Arad", "iasi": "Iași", "vaslui": "Vaslui",
    "buzau": "Buzău", "tulcea": "Tulcea", "calarasi": "Călărași", "giurgiu": "Giurgiu",
}

QA_TOPICS = [
    (r"\b(pret\w*|cost\w*|cat costa|buget\w*|ofert\w*|eur\w*|bani)\b",
     "Prețul scenariului de referință este 130.000 EUR fără TVA pentru celula UR20 completă "
     "(braț, gripper personalizat, vision SICK, 3 scanere, 2 poziții de paletizare). Oferta finală se confirmă după vizita on-site."),
    (r"\b(amortiz\w*|payback|roi|recuper\w*|rentab\w*)\b",
     "Amortizarea orientativă este 18–40 luni, în funcție de regimul de lucru: 3 schimburi → 18–24 luni, "
     "2 schimburi → 24–32 luni, 1 schimb → 34–40 luni. Nu calculăm economii salariale sau ROI personalizat."),
    (r"\b(salari\w*|economi\w*|angajat\w*|oameni|personal|manopera)\b",
     "Nu calculăm economii salariale în acest pre-audit. Afișăm doar fereastra orientativă de amortizare (18–40 luni) "
     "legată de numărul de schimburi și prețul scenariului de 130.000 EUR fără TVA."),
    (r"\b(scaner\w*|scanner\w*|siguran\w*|protecti\w*|laser\w*|accident\w*)\b",
     "Celula are 3 scanere optice de siguranță care supraveghează cele 2 poziții de paletizare: robotul lucrează "
     "pe poziția activă, iar operatorul poate schimba în siguranță paletul și separatoarele pe cealaltă poziție."),
    (r"\b(stanga|dreapta|panou|selecti\w*|parte activa|dual)\b.*\?|\b(cum|ce)\b.*\b(stanga|dreapta|panou)\b",
     "Operatorul selectează din panoul de operare partea activă de preluare: Stânga, Dreapta sau Dual "
     "(alternare între cele două europaleți). Astfel, un palet plin se schimbă manual în timp ce robotul lucrează pe celălalt."),
    (r"\b(mir|agv|amr|infoli\w*|stretch|expedi\w*|transport autonom|livrare pe camion|dispecer\w*)\b",
     "Transportul autonom MiR (AGV/AMR), înfolierea și expedierea NU sunt incluse în celula automată: scopul acoperă "
     "preluarea de pe transportor și paletizarea pe 2 europaleți. Schimbul paleților și separatoarele rămân manuale."),
    (r"\b(livrare|termen\w*|cand|instalar\w*|punere in functiune|durata proiect\w*)\b",
     "Termenul orientativ de livrare este ~4 luni (reper din proiectul PURATOS), confirmat după auditul on-site."),
    (r"\b(camer\w*|vision|vizi\w*|sick|maner\w*|toart\w*)\b.*\?",
     "Camera vision 2D SICK detectează orientarea mânerului mobil al găleții, astfel încât gripperul să prindă "
     "corect. Pentru găleți fără mâner, camera devine opțională."),
    (r"\b(cadent\w*|viteza|debit\w*|galeti pe minut|galeti/min|productivitat\w*|capacitat\w*)\b.*\?",
     "Repere testate la PURATOS (nu garanții universale): 7,4 găleți/min la 13 kg (44 găleți/palet) și 8,6 găleți/min "
     "la 5 kg (100 găleți/palet), peste ținta minimă de 6 găleți/min. Peste 8,6 găleți/min recomandăm 2 celule în paralel."),
    (r"\b(sarcin\w*|payload|greutate maxim\w*|20 ?kg|cat ridica)\b",
     "UR20 are sarcina maximă de 20 kg, care include găleata plină și gripperul pneumatic (estimat 2,8 kg). "
     "Peste 20 kg configurația este incompatibilă."),
]

QUESTION_START = r"^\s*(cat|cate|ce|cum|de ce|care|aveti|este|e|se poate|puteti|unde|cand|exista|include|ma intereseaza)\b"

FOLLOW_UPS = {
    "bucket_weight_kg": "Ce greutate are o găleată plină (kg)?",
    "line_rate_bpm": "Ce debit are linia amonte (găleți/minut sau tone pe schimb)?",
    "region": "În ce județ se află fabrica (fictivă)?",
}

NUM = r"(\d+(?:[.,]\d+)?)"


def _num(s: str) -> float:
    return float(s.replace(",", "."))


# --------------------------------------------------------------------------
# Deterministic fallback parser
# --------------------------------------------------------------------------
def parse_message(text: str, current: dict) -> dict:
    """Extract raw parameters from a Romanian message using regex/keywords.

    `current` holds the current form values (used e.g. for bucket weight when
    converting tonnage). Returns a dict with keys:
      updates, production (dict|None), confidential, risks, topics
    """
    t = calc.strip_diacritics(text)
    t = t.replace("’", "'")
    updates: dict = {}

    # Industry
    if re.search(NONFOOD_WORDS, t):
        updates["industry"] = calc.INDUSTRY_NONFOOD
    elif re.search(FOOD_WORDS, t):
        updates["industry"] = calc.INDUSTRY_FOOD

    # Content type
    if re.search(SOLID_WORDS, t):
        updates["content_type"] = "Solid-pulbere"
    if re.search(PASTE_WORDS, t):
        updates["content_type"] = "Pastă-vâscos"
    if re.search(r"\b(lichid\w*|sirop\w*|suc\w*)\b", t) or (re.search(LIQUID_WORDS, t) and "content_type" not in updates):
        updates["content_type"] = "Lichid"

    # Gripper weight
    m = re.search(r"gripper\w*\D{0,25}?" + NUM + r"\s*(?:kg|kilo)", t)
    if m:
        updates["gripper_weight_kg"] = _num(m.group(1))
    t_wo_gripper = t[: m.start()] + t[m.end():] if m else t

    # Bucket weight ("galeti de 10 kg", "10 kg/galeata", "galeata are 13 kg")
    bw = None
    for pat in (
        r"gal(?:e|ea)t\w*\s+(?:plin\w*\s+)?(?:de|are|au|cu|cantaresc|cantareste|la)?\s*(?:cate\s+)?" + NUM + r"\s*(?:kg|kilo)",
        NUM + r"\s*(?:kg|kilo\w*)\s*(?:/|pe|per|fiecare)?\s*(?:o\s+)?gal(?:e|ea)t",
        r"ambalaj\w*\s+(?:de\s+)?" + NUM + r"\s*kg",
        r"(?:greutate|cantaresc|cantareste)\D{0,15}" + NUM + r"\s*kg",
    ):
        m = re.search(pat, t_wo_gripper)
        if m:
            bw = _num(m.group(1))
            break
    if bw is None:
        # a lone "N kg" that isn't a rate or a production quantity
        kg_hits = [
            mm for mm in re.finditer(NUM + r"\s*kg\b(?!\s*(?:/|pe)\s*(?:schimb|zi|ora|h|min))", t_wo_gripper)
        ]
        if len(kg_hits) == 1 and _num(kg_hits[0].group(1)) <= 60:
            bw = _num(kg_hits[0].group(1))
    if bw is not None:
        updates["bucket_weight_kg"] = bw

    # Handle
    if re.search(r"\b(fara|nu au|nu are|lipsa)\s+(?:\w+\s+)?(toart\w*|maner\w*)", t):
        updates["has_handle"] = False
    elif re.search(r"\b(toart\w*|maner\w*)", t):
        updates["has_handle"] = True

    # Shifts
    shifts = None
    m = re.search(r"\b([123])\s*(?:x|×)\s*8\b", t)
    if m:
        shifts = int(m.group(1))
    m = re.search(r"\b([123])\s*schimb", t)
    if m:
        shifts = int(m.group(1))
    if re.search(r"\b(un|unu|un singur|singur)\s+schimb\b|\bintr-un schimb\b|\bintr-un singur schimb\b", t):
        shifts = 1
    if re.search(r"\bdoua\s+schimburi\b", t):
        shifts = 2
    if re.search(r"\btrei\s+schimburi\b|non[- ]?stop|24/7|24 de ore|continuu", t):
        shifts = 3
    if shifts:
        updates["shifts"] = shifts

    # Shift duration
    shift_hours = 8.0
    m = re.search(r"schimb\w*\s+(?:de\s+)?" + NUM + r"\s*(?:ore|h)\b", t) or re.search(NUM + r"\s*(?:ore|h)\s*(?:pe|/)\s*schimb", t)
    if m:
        shift_hours = _num(m.group(1))

    # Line rate (explicit)
    m = re.search(NUM + r"\s*(?:galeti|buc\w*|bucati|ambalaje)?\s*(?:/|pe|per)\s*(?:minut|min)\b", t)
    if m:
        updates["line_rate_bpm"] = _num(m.group(1))
    else:
        m = re.search(NUM + r"\s*(?:galeti|buc\w*|bucati|ambalaje)\s*(?:/|pe|per|la)\s*(?:ora|h)\b", t)
        if m:
            updates["line_rate_bph"] = _num(m.group(1))

    # Production quantity (tonnes or kg per shift/day/hour)
    production = None
    m = re.search(NUM + r"\s*(tone|tona|t)\b(?:\s+de\s+[a-z]+)?(?:\s+\w+){0,3}?\s*(?:/|pe|per|intr-un|intr-o|in)\s*(schimb|zi|ora|h)\b", t) \
        or re.search(NUM + r"\s*(kg|kilograme)\b(?:\s+de\s+[a-z]+)?(?:\s+\w+){0,3}?\s*(?:/|pe|per|intr-un|intr-o|in)\s*(schimb|zi|ora|h)\b", t)
    if m:
        qty = _num(m.group(1))
        unit = m.group(2)
        kg = qty * 1000 if unit in ("tone", "tona", "t") else qty
        period = {"h": "ora"}.get(m.group(3), m.group(3))
        production = {"production_kg": kg, "period": period, "shift_hours": shift_hours}

    # Side selection
    if re.search(r"\b(dual|ambele (?:parti|pozitii|laturi)|alternativ|ambele)\b", t):
        updates["side_selection"] = "Dual"
    elif re.search(r"\b(partea |pe |doar |numai )?stanga\b", t) and not re.search(r"\bdreapta\b", t):
        updates["side_selection"] = "Stânga"
    elif re.search(r"\bdreapta\b", t) and not re.search(r"\bstanga\b", t):
        updates["side_selection"] = "Dreapta"

    # Air supply
    if re.search(r"aer\w*", t):
        if re.search(r"(nu stiu|nu sunt sigur|habar|neclar|de verificat)\D{0,30}aer|aer\D{0,30}(nu stiu|nu sunt sigur|neclar)", t):
            updates["air_supply"] = "Nu știu"
        elif re.search(r"(nu avem|fara|lipsa|lipseste|nu exista)\D{0,20}aer|aer comprimat\D{0,15}(nu avem|lipseste|nu exista)", t):
            updates["air_supply"] = "Nu"
        elif re.search(r"aer comprimat", t):
            updates["air_supply"] = "Da"

    # Pallet equipment
    if re.search(r"\bstivuitor\w*", t):
        updates["pallet_equipment"] = "Stivuitor"
    elif re.search(r"\btranspalet\w*", t):
        updates["pallet_equipment"] = "Transpalet"
    elif re.search(r"\bliz\w*", t):
        updates["pallet_equipment"] = "Liză"

    # Region
    county = find_county(t)
    if county:
        updates["region"] = county

    # Confidential info
    confidential: list[str] = []
    if re.search(r"confidential\w*|nu (?:pot|putem|vreau sa) (?:spune|da|divulga|comunica)|secret\w*|nu va pot (?:spune|da)", t):
        if re.search(r"debit|cadent|productie|tone|volum", t):
            confidential.append("Debit exact linie de vârf")
        if re.search(r"compan\w*|firm\w*|nume", t):
            confidential.append("Nume companie")
        if re.search(r"retet\w*|produs", t):
            confidential.append("Rețetă / tip produs")
        if re.search(r"locati\w*|adres\w*|oras|judet", t):
            confidential.append("Locație exactă fabrică")
        if re.search(r"greutat\w*", t):
            confidential.append("Greutate exactă găleată")
        if not confidential:
            confidential.append("Informație marcată confidențial în discuție")

    # Unstructured risks
    risks = [label for pat, label in RISK_PATTERNS if re.search(pat, t)]

    # Q&A topics
    is_question = "?" in text or bool(re.search(QUESTION_START, t))
    topics = []
    if is_question:
        for pat, answer in QA_TOPICS:
            if re.search(pat, t) and answer not in topics:
                topics.append(answer)

    return {
        "updates": updates,
        "production": production,
        "confidential": confidential,
        "risks": risks,
        "topics": topics[:2],
        "is_question": is_question,
    }


def find_county(t: str) -> str | None:
    """Find a Romanian county (or major city) in diacritic-free text."""
    for city in sorted(CITY_TO_COUNTY, key=len, reverse=True):
        if re.search(r"\b" + re.escape(city) + r"\b", t):
            return CITY_TO_COUNTY[city]
    for county in sorted(calc.COUNTIES, key=len, reverse=True):
        key = calc.strip_diacritics(county)
        if county == "Olt":
            if re.search(r"\b(judetul|jud\.?|zona|in)\s+olt\b", t):
                return county
            continue
        if county == "Alba":
            if re.search(r"\balba\b(?!\s+iulia)", t) and re.search(r"\b(judetul|jud\.?|zona|in|langa)\s+alba\b", t):
                return county
            continue
        if re.search(r"\b" + re.escape(key) + r"\b", t):
            return county
    return None


# --------------------------------------------------------------------------
# Normalisation of values coming from the LLM
# --------------------------------------------------------------------------
def _to_float(v):
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(str(v).replace(",", "."))
    except ValueError:
        return None
    return f


def normalize_llm_updates(raw: dict) -> tuple[dict, dict | None]:
    """Validate/whitelist LLM form_updates. Returns (updates, production)."""
    updates: dict = {}
    if not isinstance(raw, dict):
        return updates, None
    s = lambda k: calc.strip_diacritics(str(raw.get(k) or "")).strip()

    ind = s("industry")
    if ind.startswith("non"):
        updates["industry"] = calc.INDUSTRY_NONFOOD
    elif ind.startswith("aliment"):
        updates["industry"] = calc.INDUSTRY_FOOD

    for key in ("bucket_weight_kg", "gripper_weight_kg", "line_rate_bpm", "line_rate_bph"):
        f = _to_float(raw.get(key))
        if f is not None and 0 < f < 10000:
            updates[key] = f

    ct = s("content_type")
    if ct.startswith("lich"):
        updates["content_type"] = "Lichid"
    elif ct.startswith("past") or ct.startswith("vasc"):
        updates["content_type"] = "Pastă-vâscos"
    elif ct.startswith("solid") or ct.startswith("pulb"):
        updates["content_type"] = "Solid-pulbere"

    hh = raw.get("has_handle")
    if isinstance(hh, bool):
        updates["has_handle"] = hh
    elif s("has_handle") in ("da", "true", "yes"):
        updates["has_handle"] = True
    elif s("has_handle") in ("nu", "false", "no"):
        updates["has_handle"] = False

    sh = _to_float(raw.get("shifts"))
    if sh in (1.0, 2.0, 3.0):
        updates["shifts"] = int(sh)

    side = s("side_selection")
    if side.startswith("st"):
        updates["side_selection"] = "Stânga"
    elif side.startswith("dr"):
        updates["side_selection"] = "Dreapta"
    elif side.startswith("du") or side.startswith("amb"):
        updates["side_selection"] = "Dual"

    region = s("region")
    if region and region != "null":
        county = find_county(region)
        if county:
            updates["region"] = county

    air = s("air_supply").replace("_", " ")
    if air in ("da", "true"):
        updates["air_supply"] = "Da"
    elif air in ("nu", "false"):
        updates["air_supply"] = "Nu"
    elif "stiu" in air:
        updates["air_supply"] = "Nu știu"

    pe = s("pallet_equipment")
    if pe.startswith("liz"):
        updates["pallet_equipment"] = "Liză"
    elif pe.startswith("trans"):
        updates["pallet_equipment"] = "Transpalet"
    elif pe.startswith("stiv"):
        updates["pallet_equipment"] = "Stivuitor"

    production = None
    pkg = _to_float(raw.get("production_kg"))
    if pkg and pkg > 0:
        period = s("period") or "schimb"
        hours = _to_float(raw.get("shift_hours")) or 8.0
        production = {"production_kg": pkg, "period": "zi" if period.startswith("zi") else "schimb", "shift_hours": hours}
    return updates, production


def _clean_list(items, limit: int = 8) -> list[str]:
    out = []
    if isinstance(items, list):
        for it in items:
            if isinstance(it, str) and it.strip() and it.strip().lower() != "null":
                text = it.strip()[:160]
                if text not in out:
                    out.append(text)
    return out[:limit]


# --------------------------------------------------------------------------
# Deterministic post-processing (all math here, never in the LLM)
# --------------------------------------------------------------------------
def finalize_updates(updates: dict, production: dict | None, current: dict) -> tuple[dict, str | None]:
    """Convert per-hour rates and production quantities into găleți/min."""
    updates = dict(updates)
    note = None
    if "line_rate_bph" in updates:
        bph = updates.pop("line_rate_bph")
        if "line_rate_bpm" not in updates:
            updates["line_rate_bpm"] = round(bph / 60.0, 2)
            note = f"{calc.fmt_num(bph, 0)} găleți/oră / 60 min ≈ {calc.fmt_num(bph / 60.0, 2)} găleți/min"
    if production and "line_rate_bpm" not in updates:
        bucket = updates.get("bucket_weight_kg") or current.get("bucket_weight_kg")
        shifts = updates.get("shifts") or current.get("shifts") or 1
        hours = production.get("shift_hours") or 8.0
        if production.get("period") == "zi":
            minutes = hours * 60 * shifts
        elif production.get("period") == "ora":
            minutes = 60
        else:
            minutes = hours * 60
        conv = calc.rate_from_production(production["production_kg"], bucket or 0, minutes)
        if conv:
            updates["line_rate_bpm"] = conv["rate_bpm"]
            note = conv["explanation"]
    if "line_rate_bpm" in updates:
        updates["line_rate_bpm"] = round(float(updates["line_rate_bpm"]), 2)
    return updates, note


FIELD_LABELS = {
    "industry": "Industrie",
    "bucket_weight_kg": "Greutate găleată",
    "gripper_weight_kg": "Greutate gripper",
    "content_type": "Tip conținut",
    "has_handle": "Mâner",
    "line_rate_bpm": "Debit linie",
    "shifts": "Schimburi/zi",
    "side_selection": "Selecție preluare",
    "region": "Județ",
    "air_supply": "Aer comprimat",
    "pallet_equipment": "Echipament schimb paleți",
}


def describe_value(key: str, value) -> str:
    if key in ("bucket_weight_kg", "gripper_weight_kg"):
        return f"{calc.fmt_num(value)} kg"
    if key == "line_rate_bpm":
        return f"{calc.fmt_num(value, 2)} găleți/min"
    if key == "has_handle":
        return "Da" if value else "Nu"
    if key == "region":
        return f"{value} (hub {calc.hub_for_county(value)})"
    return str(value)


def _fallback_reply(parsed: dict, updates: dict, note: str | None, known: set[str]) -> str:
    parts: list[str] = []
    if parsed["topics"]:
        parts.extend(parsed["topics"])
    if updates:
        changes = "; ".join(f"{FIELD_LABELS[k]}: {describe_value(k, v)}" for k, v in updates.items() if k in FIELD_LABELS)
        parts.append(f"Am actualizat formularul — {changes}.")
    if parsed["risks"]:
        parts.append("Am adăugat în raport riscurile specifice: " + "; ".join(parsed["risks"]) + ".")
    if parsed["confidential"]:
        parts.append("Am marcat ca «Confidențial / De verificat on-site»: " + ", ".join(parsed["confidential"]) + ".")
    if not parts:
        parts.append(
            "Nu am identificat parametri tehnici în mesaj. Descrieți linia (ex: «găleți de 10 kg cu toartă, 2 schimburi, "
            "5 tone pe schimb, lângă Cluj») sau întrebați despre preț, amortizare, scanere, selecția Stânga/Dreapta sau ce nu este inclus."
        )
    return " ".join(parts)


def _follow_up(known: set[str]) -> str | None:
    for key, question in FOLLOW_UPS.items():
        if key not in known:
            return question
    return None


def process_message(
    text: str,
    current: dict,
    known_fields: set[str] | None = None,
    history: list[dict] | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> dict:
    """Main entry point used by app.py."""
    known = set(known_fields or set())
    parsed = parse_message(text, current)

    llm = None
    error = None
    if api_key:
        llm, error = _call_openrouter(text, current, history or [], api_key, model or DEFAULT_MODEL)

    if llm is not None:
        llm_updates, llm_production = normalize_llm_updates(llm.get("form_updates") or {})
        # Deterministic parser wins on values it found explicitly; LLM fills gaps.
        merged = {**llm_updates, **parsed["updates"]}
        production = parsed["production"] or llm_production
        if "line_rate_bpm" in parsed["updates"] or "line_rate_bph" in parsed["updates"]:
            production = None
        if production:
            merged.pop("line_rate_bpm", None)  # never trust LLM arithmetic over a stated production
        updates, note = finalize_updates(merged, production, current)
        risks = _clean_list(llm.get("custom_risks")) + [r for r in parsed["risks"]]
        confidential = _clean_list(llm.get("confidential_fields")) + parsed["confidential"]
        reply = str(llm.get("reply") or "").strip() or _fallback_reply(parsed, updates, note, known)
        source = "llm"
    else:
        updates, note = finalize_updates(parsed["updates"], parsed["production"], current)
        risks = parsed["risks"]
        confidential = parsed["confidential"]
        reply = _fallback_reply(parsed, updates, note, known)
        source = "fallback"

    risks = _dedupe(risks)
    confidential = _dedupe(confidential)
    known |= set(updates.keys())
    if "Debit exact linie de vârf" in confidential:
        known.add("line_rate_bpm")
    ready = all(k in known for k in FOLLOW_UPS)

    if source == "fallback" and not ready and (updates or not parsed["topics"]):
        q = _follow_up(known)
        if q:
            reply += f" {q}"

    return {
        "reply": reply,
        "form_updates": updates,
        "confidential_fields": confidential,
        "custom_risks": risks,
        "ready_for_report": ready,
        "source": source,
        "calc_note": note,
        "error": error,
        "known_fields": known,
    }


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for it in items:
        k = calc.strip_diacritics(it)
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


def _call_openrouter(text: str, current: dict, history: list[dict], api_key: str, model: str):
    """Returns (parsed_json | None, error_message | None). Never raises."""
    context = (
        "Valorile curente din formular (pot fi implicite, nu neapărat confirmate de utilizator): "
        + json.dumps(current, ensure_ascii=False)
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "system", "content": context}]
    for msg in history[-6:]:
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({"role": msg["role"], "content": str(msg["content"])[:1500]})
    messages.append({"role": "user", "content": text[:2000]})
    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                     "X-Title": "UR20 Pre-Audit Demo"},
            json={"model": model, "messages": messages, "temperature": 0,
                  "response_format": {"type": "json_object"}, "max_tokens": 700},
            timeout=TIMEOUT_S,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _extract_json(content), None
    except requests.Timeout:
        return None, "timeout"
    except Exception as exc:  # network, HTTP, JSON shape
        return None, type(exc).__name__


def _extract_json(content: str) -> dict:
    content = (content or "").strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.S)
        if not m:
            raise
        data = json.loads(m.group(0))
    if not isinstance(data, dict):
        raise ValueError("JSON root is not an object")
    return data
