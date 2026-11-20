"""Deterministic engineering core for the UR20 palletizing pre-qualification.

Every number shown in the app (payload, cadence load, timings, payback window,
hub allocation, verdict, match score) is computed here in plain Python.
The AI consultant never performs calculations; it only extracts parameters.
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Constants (PURATOS reference facts + scenario commercial data)
# --------------------------------------------------------------------------
UR20_MAX_PAYLOAD_KG = 20.0
BENCHMARK_LIGHT_BPM = 8.6   # 5 kg buckets, 100 per pallet (PURATOS test)
BENCHMARK_HEAVY_BPM = 7.4   # 13 kg buckets, 44 per pallet (PURATOS test)
LIGHT_BUCKET_THRESHOLD_KG = 5.0   # 8,6/min was tested only on 5 kg buckets
MIN_TARGET_BPM = 6.0
BOTTLENECK_BPM = 8.6
LOW_MARGIN_KG = 1.5
SCENARIO_PRICE = "130.000 EUR (fără TVA)"
DELIVERY_ESTIMATE = "~4 luni"
PAYBACK_RANGE = "18–40 luni"
DEFAULT_GRIPPER_KG = 5.0   # assumption, same as the financial model
SHIFT_HOURS = 8.0          # assumption for the manual-lifting estimate

LABEL_FACT = "Rezultate de test PURATOS — nu reprezintă garanții universale"
LABEL_ESTIMATE = "Estimare bazată pe ipotezele introducerii"

# Form option values (Romanian UI labels are the canonical values)
INDUSTRY_FOOD = "Alimentară (găleți plastic)"
INDUSTRY_NONFOOD = "Non-alimentară"
INDUSTRIES = [INDUSTRY_FOOD, INDUSTRY_NONFOOD]

CONTENT_TYPES = ["Lichid", "Pastă-vâscos", "Solid-pulbere"]
YES_NO = ["Da", "Nu"]
AIR_OPTIONS = ["Da", "Nu", "Nu știu"]
PALLET_EQUIPMENT = ["Liză", "Transpalet", "Stivuitor"]
SIDES = ["Stânga", "Dreapta", "Dual"]
SHIFTS = [1, 2, 3]

PALLET_PRESET_5 = "Preset 5 kg (100 găleți, 4 straturi)"
PALLET_PRESET_13 = "Preset 13 kg (44 găleți, 4 straturi)"
PALLET_CUSTOM = "Custom"
PALLET_CONFIGS = [PALLET_PRESET_5, PALLET_PRESET_13, PALLET_CUSTOM]
PALLET_PRESET_VALUES = {
    PALLET_PRESET_5: (100, 4),
    PALLET_PRESET_13: (44, 4),
}

HUB_SOUTH = "Dragomirești-Deal"
HUB_EAST = "Iași"
HUB_WEST = "Timișoara"
HUBS = [HUB_SOUTH, HUB_EAST, HUB_WEST]

# Deterministic county -> nearest Tech-Con hub mapping (41 counties + București)
COUNTY_TO_HUB: dict[str, str] = {
    # South: Muntenia, Oltenia, Dobrogea, București-Ilfov, Brașov, Sibiu, Covasna
    "București": HUB_SOUTH, "Ilfov": HUB_SOUTH, "Prahova": HUB_SOUTH,
    "Dâmbovița": HUB_SOUTH, "Argeș": HUB_SOUTH, "Giurgiu": HUB_SOUTH,
    "Teleorman": HUB_SOUTH, "Călărași": HUB_SOUTH, "Ialomița": HUB_SOUTH,
    "Buzău": HUB_SOUTH, "Brăila": HUB_SOUTH, "Constanța": HUB_SOUTH,
    "Tulcea": HUB_SOUTH, "Olt": HUB_SOUTH, "Dolj": HUB_SOUTH, "Gorj": HUB_SOUTH,
    "Mehedinți": HUB_SOUTH, "Vâlcea": HUB_SOUTH, "Brașov": HUB_SOUTH,
    "Sibiu": HUB_SOUTH, "Covasna": HUB_SOUTH,
    # Moldova
    "Iași": HUB_EAST, "Bacău": HUB_EAST, "Suceava": HUB_EAST, "Neamț": HUB_EAST,
    "Botoșani": HUB_EAST, "Vaslui": HUB_EAST, "Galați": HUB_EAST,
    "Vrancea": HUB_EAST, "Harghita": HUB_EAST,
    # West, Transylvania West / North-West
    "Timiș": HUB_WEST, "Arad": HUB_WEST, "Bihor": HUB_WEST, "Cluj": HUB_WEST,
    "Caraș-Severin": HUB_WEST, "Hunedoara": HUB_WEST, "Alba": HUB_WEST,
    "Satu Mare": HUB_WEST, "Maramureș": HUB_WEST, "Sălaj": HUB_WEST,
    "Mureș": HUB_WEST, "Bistrița-Năsăud": HUB_WEST,
}
PAYBACK_BY_SHIFTS = {3: "18–24 luni", 2: "24–32 luni", 1: "34–40 luni"}

VERDICT_GREEN = "VERDE"
VERDICT_YELLOW = "GALBEN"
VERDICT_RED = "ROȘU"
VERDICT_TITLES = {
    VERDICT_GREEN: "COMPATIBIL UR20 — POTRIVIRE RIDICATĂ",
    VERDICT_YELLOW: "FEZABIL CU VALIDARE TEHNICĂ / RISCURI",
    VERDICT_RED: "INCOMPATIBIL UR20 (Suprasarcină)",
}
# Short labels used in the CRM (Verde / Galben / Roșu)
VERDICT_CRM = {VERDICT_GREEN: "Verde", VERDICT_YELLOW: "Galben", VERDICT_RED: "Roșu"}

CONFIDENTIAL_FIELD_OPTIONS = [
    "Nume companie",
    "Debit exact linie de vârf",
    "Greutate exactă găleată",
    "Rețetă / tip produs",
    "Volume anuale de producție",
    "Layout hală / amprentă la sol",
    "Furnizor ambalaje",
    "Locație exactă fabrică",
]

ONSITE_ACTIONS = [
    "Testare fizică pe mostre reale de găleți (prindere gripper, stabilitate, orientare mâner).",
    "Audit amprentă la sol și flux paleți/operator (acces liză/transpalet/stivuitor, zone scanere).",
    "Audit semnale electrice/pneumatice transportor amonte (I/O, aer comprimat, presiune și debit).",
]

OUT_OF_SCOPE = [
    "Transport autonom paleți (MiR AGV/AMR)",
    "Înfoliere (stretch-wrapping)",
    "Expediere / dispecerizare",
]
MANUAL_TASKS = [
    "Schimbarea paleților plini (manual, de operator)",
    "Așezarea separatoarelor între straturi (manual, de operator)",
]


def strip_diacritics(text: str) -> str:
    """Lowercase + remove Romanian diacritics (ș/ş, ț/ţ, ă, â, î)."""
    norm = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in norm if not unicodedata.combining(ch)).lower()


COUNTIES = sorted(COUNTY_TO_HUB.keys(), key=strip_diacritics)


# --------------------------------------------------------------------------
# Data structures
# --------------------------------------------------------------------------
@dataclass
class SimulationInput:
    industry: str = INDUSTRY_FOOD
    bucket_weight_kg: float = 13.0
    gripper_weight_kg: float = DEFAULT_GRIPPER_KG
    content_type: str = "Pastă-vâscos"
    has_handle: bool = True
    line_rate_bpm: float = 6.5
    pallet_config: str = PALLET_PRESET_13
    custom_buckets_per_pallet: int = 60
    custom_layers: int = 4
    side_selection: str = "Dual"
    shifts: int = 2
    air_supply: str = "Da"
    pallet_equipment: str = "Transpalet"
    county: str = "Ilfov"
    confidential_fields: list[str] = field(default_factory=list)
    custom_risks: list[str] = field(default_factory=list)

    @property
    def buckets_per_pallet(self) -> int:
        if self.pallet_config in PALLET_PRESET_VALUES:
            return PALLET_PRESET_VALUES[self.pallet_config][0]
        return int(self.custom_buckets_per_pallet)

    @property
    def layers(self) -> int:
        if self.pallet_config in PALLET_PRESET_VALUES:
            return PALLET_PRESET_VALUES[self.pallet_config][1]
        return int(self.custom_layers)


@dataclass
class Risk:
    title: str
    detail: str
    source: str = "auto"  # "auto" | "chat" | "manual"
    affects_verdict: bool = True


@dataclass
class SimulationResult:
    inp: SimulationInput
    payload_total: float
    safety_margin_kg: float
    payload_pct: float
    benchmark_bpm: float
    benchmark_label: str
    load_pct: float
    bottleneck: bool
    above_benchmark: bool
    fill_time_min: float
    separator_time_min: float
    buckets_per_layer: float
    payback: str
    hub: str
    manual_tonnes_shift: float
    manual_lifts_per_min_operator: float
    verdict: str
    verdict_title: str
    score: int
    risks: list[Risk]
    hardware: list[tuple[str, str]]
    notes: list[str]

    @property
    def verdict_crm(self) -> str:
        return VERDICT_CRM[self.verdict]


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def validate(inp: SimulationInput) -> list[str]:
    """Return a list of Romanian error messages; empty list means valid."""
    errors: list[str] = []
    checks = [
        (inp.bucket_weight_kg, "Greutate găleată plină (kg)"),
        (inp.gripper_weight_kg, "Greutate gripper pneumatic estimată (kg)"),
        (inp.line_rate_bpm, "Debit linie amonte (găleți/minut)"),
        (inp.buckets_per_pallet, "Număr găleți pe palet"),
        (inp.layers, "Număr straturi pe palet"),
    ]
    for value, label in checks:
        if value is None or not _is_finite(value):
            errors.append(f"{label}: valoare lipsă sau invalidă.")
        elif value <= 0:
            errors.append(f"{label}: trebuie să fie strict mai mare decât 0 (valoare introdusă: {fmt_num(value)}).")
    if not errors and inp.layers > inp.buckets_per_pallet:
        errors.append(
            "Număr straturi pe palet: nu poate depăși numărul de găleți pe palet "
            f"({inp.layers} straturi > {inp.buckets_per_pallet} găleți)."
        )
    if inp.industry not in INDUSTRIES:
        errors.append("Industrie: selectați o opțiune validă.")
    if inp.side_selection not in SIDES:
        errors.append("Selecție preluare operator: selectați Stânga, Dreapta sau Dual.")
    if inp.shifts not in SHIFTS:
        errors.append("Număr schimburi/zi: selectați 1, 2 sau 3.")
    if inp.county not in COUNTY_TO_HUB:
        errors.append("Regiune / Județ: selectați un județ din listă.")
    return errors


def _is_finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


# --------------------------------------------------------------------------
# Core formulas
# --------------------------------------------------------------------------
def benchmark_for_weight(bucket_weight_kg: float) -> float:
    return BENCHMARK_LIGHT_BPM if bucket_weight_kg <= LIGHT_BUCKET_THRESHOLD_KG else BENCHMARK_HEAVY_BPM


def hub_for_county(county: str) -> str:
    return COUNTY_TO_HUB.get(county, HUB_SOUTH)


def payback_for_shifts(shifts: int) -> str:
    return PAYBACK_BY_SHIFTS.get(int(shifts), PAYBACK_BY_SHIFTS[1])


def rate_from_production(production_kg: float, bucket_weight_kg: float, period_minutes: float) -> dict | None:
    """Convert a produced mass over a period into buckets/minute.

    Returns the intermediate values so the UI/chat can show the deterministic
    calculation, e.g. 10000 kg / 10 kg = 1000 găleți / 480 min ≈ 2,08 găleți/min.
    """
    if production_kg <= 0 or bucket_weight_kg <= 0 or period_minutes <= 0:
        return None
    buckets = production_kg / bucket_weight_kg
    rate = buckets / period_minutes
    return {
        "production_kg": production_kg,
        "bucket_weight_kg": bucket_weight_kg,
        "buckets": buckets,
        "period_minutes": period_minutes,
        "rate_bpm": round(rate, 2),
        "explanation": (
            f"{fmt_num(production_kg, 0)} kg / {fmt_num(bucket_weight_kg)} kg = "
            f"{fmt_num(buckets, 0)} găleți / {fmt_num(period_minutes, 0)} min ≈ "
            f"{fmt_num(rate, 2)} găleți/min"
        ),
    }


def simulate(inp: SimulationInput) -> SimulationResult:
    """Run the deterministic pre-qualification. Assumes `validate(inp)` is empty."""
    payload_total = round(inp.bucket_weight_kg + inp.gripper_weight_kg, 2)
    margin = round(UR20_MAX_PAYLOAD_KG - payload_total, 2)
    payload_pct = payload_total / UR20_MAX_PAYLOAD_KG * 100

    benchmark = benchmark_for_weight(inp.bucket_weight_kg)
    benchmark_label = (
        "8,6 găleți/min (reper PURATOS 5 kg, 100 găleți/palet)"
        if benchmark == BENCHMARK_LIGHT_BPM
        else "7,4 găleți/min (reper PURATOS 13 kg, 44 găleți/palet)"
    )
    load_pct = inp.line_rate_bpm / benchmark * 100
    bottleneck = inp.line_rate_bpm > BOTTLENECK_BPM
    above_benchmark = inp.line_rate_bpm > benchmark

    n = inp.buckets_per_pallet
    layers = inp.layers
    # The cell cannot place faster than its tested rate, so timings use the slower of the two.
    effective_rate = min(inp.line_rate_bpm, benchmark)
    fill_time = n / effective_rate
    per_layer = n / layers
    separator_time = per_layer / effective_rate
    manual_tonnes_shift = inp.line_rate_bpm * 60 * SHIFT_HOURS * inp.bucket_weight_kg / 1000
    manual_lifts_per_min_operator = inp.line_rate_bpm / 2  # 2 operators per shift, as at PURATOS

    overload = payload_total > UR20_MAX_PAYLOAD_KG
    risks = detect_risks(inp, payload_total, margin, benchmark, overload)

    has_yellow_trigger = any(r.affects_verdict for r in risks) or bool(inp.confidential_fields)
    if overload:
        verdict = VERDICT_RED
    elif has_yellow_trigger:
        verdict = VERDICT_YELLOW
    else:
        verdict = VERDICT_GREEN

    score = match_score(inp, payload_total, margin, benchmark, verdict)

    hardware = [
        ("Braț colaborativ Universal Robots UR20 (sarcină max. 20 kg)", "Inclus"),
        ("Gripper pneumatic personalizat pentru găleți", "Inclus"),
        (
            "Cameră vision 2D SICK (detectare orientare mâner)",
            "Inclus — necesar (găleți cu mâner mobil)" if inp.has_handle else "Opțional / nu este necesar (găleți fără mâner)",
        ),
        ("3 scanere optice de siguranță (2 poziții de paletizare)", "Inclus"),
        ("2 poziții de paletizare pe europaleți (Stânga / Dreapta)", "Inclus"),
        ("Semnale I/O de interfață cu transportorul de alimentare", "Inclus — de validat on-site"),
    ]

    notes: list[str] = []
    if inp.pallet_config == PALLET_PRESET_5 and inp.bucket_weight_kg > LIGHT_BUCKET_THRESHOLD_KG:
        notes.append("Configurația de palet (preset 5 kg) nu corespunde greutății găleții — schema de paletizare trebuie validată.")
    if inp.pallet_config == PALLET_PRESET_13 and inp.bucket_weight_kg <= LIGHT_BUCKET_THRESHOLD_KG:
        notes.append("Configurația de palet (preset 13 kg) este atipică pentru găleți ușoare — schema de paletizare trebuie validată.")
    if per_layer != int(per_layer):
        notes.append(
            f"Numărul de găleți pe strat nu este întreg ({fmt_num(per_layer, 2)}) — straturile vor fi inegale; schema trebuie revizuită."
        )
    if inp.line_rate_bpm < MIN_TARGET_BPM:
        notes.append(
            f"Debitul liniei ({fmt_num(inp.line_rate_bpm, 2)} găleți/min) este sub ținta minimă de 6 găleți/min a proiectului de referință — "
            "celula va avea timp de așteptare (capacitate disponibilă)."
        )

    return SimulationResult(
        inp=inp,
        payload_total=payload_total,
        safety_margin_kg=margin,
        payload_pct=payload_pct,
        benchmark_bpm=benchmark,
        benchmark_label=benchmark_label,
        load_pct=load_pct,
        bottleneck=bottleneck,
        above_benchmark=above_benchmark,
        fill_time_min=fill_time,
        separator_time_min=separator_time,
        buckets_per_layer=per_layer,
        payback=payback_for_shifts(inp.shifts),
        hub=hub_for_county(inp.county),
        manual_tonnes_shift=manual_tonnes_shift,
        manual_lifts_per_min_operator=manual_lifts_per_min_operator,
        verdict=verdict,
        verdict_title=VERDICT_TITLES[verdict],
        score=score,
        risks=risks,
        hardware=hardware,
        notes=notes,
    )


def detect_risks(inp: SimulationInput, payload_total: float, margin: float, benchmark: float, overload: bool) -> list[Risk]:
    risks: list[Risk] = []
    if overload:
        risks.append(Risk(
            "Suprasarcină UR20",
            f"Sarcina totală {fmt_num(payload_total)} kg (găleată + gripper) depășește limita de 20 kg cu "
            f"{fmt_num(payload_total - UR20_MAX_PAYLOAD_KG)} kg. Celula UR20 nu poate fi ofertată în această configurație.",
        ))
    elif margin < LOW_MARGIN_KG:
        risks.append(Risk(
            "Marjă mică de sarcină",
            f"Marja de siguranță față de 20 kg este de doar {fmt_num(margin)} kg (< 1,5 kg). "
            "Greutatea reală a găleții și a gripperului trebuie cântărită on-site.",
        ))
    if inp.line_rate_bpm > BOTTLENECK_BPM:
        risks.append(Risk(
            "Gâtuire de flux (debit > 8,6 găleți/min)",
            "Debitul liniei depășește cel mai bun reper testat. Recomandare: 2 celule UR20 în paralel sau analiză flux amonte/aval.",
        ))
    elif inp.line_rate_bpm > benchmark:
        risks.append(Risk(
            "Debit peste reperul testat",
            f"Debitul de {fmt_num(inp.line_rate_bpm, 2)} găleți/min depășește reperul PURATOS de "
            f"{fmt_num(benchmark)} găleți/min pentru această clasă de greutate — cadența trebuie validată prin test.",
        ))
    if inp.industry == INDUSTRY_NONFOOD:
        risks.append(Risk(
            "Industrie non-alimentară — validare separată",
            "Referința PURATOS acoperă găleți alimentare din plastic. Ambalajul, materialul și cerințele de mediu "
            "(ex. ATEX, solvenți) necesită validare tehnică separată.",
        ))
    if inp.air_supply == "Nu":
        risks.append(Risk(
            "Lipsă aer comprimat",
            "Gripperul pneumatic necesită aer comprimat. Este necesară o sursă (compresor/rețea) — cost și termen suplimentar.",
        ))
    elif inp.air_supply == "Nu știu":
        risks.append(Risk(
            "Incertitudine aer comprimat",
            "Disponibilitatea, presiunea și debitul aerului comprimat trebuie verificate la vizita on-site.",
        ))
    if inp.content_type == "Lichid":
        risks.append(Risk(
            "Conținut lichid — balans ambalaj",
            "Lichidul se deplasează în găleată la accelerații; profilul de mișcare și etanșeitatea capacului trebuie validate.",
        ))
    for text in inp.custom_risks:
        risks.append(Risk("Risc specific semnalat", text, source="chat"))
    return risks


def match_score(inp: SimulationInput, payload_total: float, margin: float, benchmark: float, verdict: str) -> int:
    """Deterministic 0–100 match score, banded by verdict."""
    if verdict == VERDICT_RED:
        over = payload_total - UR20_MAX_PAYLOAD_KG
        return int(max(0, min(30, round(30 - over * 10))))

    score = 100.0
    if inp.line_rate_bpm > BOTTLENECK_BPM:
        score -= 25
    elif inp.line_rate_bpm > benchmark:
        score -= 12
    if inp.industry == INDUSTRY_NONFOOD:
        score -= 10
    if inp.air_supply == "Nu":
        score -= 15
    elif inp.air_supply == "Nu știu":
        score -= 8
    if inp.content_type == "Lichid":
        score -= 8
    if margin < LOW_MARGIN_KG:
        score -= 10
    score -= min(10, 3 * len(inp.confidential_fields))
    score -= min(12, 4 * len(inp.custom_risks))
    if inp.line_rate_bpm < MIN_TARGET_BPM:
        score -= 3  # under-utilised cell

    if verdict == VERDICT_GREEN:
        return int(max(80, min(100, round(score))))
    return int(max(40, min(79, round(score))))


# --------------------------------------------------------------------------
# Formatting helpers (Romanian number format: comma decimal, dot thousands)
# --------------------------------------------------------------------------
def fmt_num(value: float, decimals: int = 1) -> str:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if decimals == 0:
        s = f"{value:,.0f}"
    else:
        s = f"{value:,.{decimals}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_minutes(minutes: float) -> str:
    total_seconds = int(round(minutes * 60))
    m, s = divmod(total_seconds, 60)
    if m and s:
        return f"{fmt_num(minutes, 1)} min (≈ {m} min {s:02d} s)"
    if m:
        return f"{fmt_num(minutes, 1)} min"
    return f"{s} s"
