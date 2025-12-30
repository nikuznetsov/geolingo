import json
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
GEO_PATH = BASE_DIR / "static" / "world_50m.geojson"
OUT_PATH = BASE_DIR / "data" / "world_data.json"

# Пул языков (можно расширять)
LANG_POOL = [
    "English", "Spanish", "French", "Arabic", "Russian", "Portuguese", "German",
    "Italian", "Dutch", "Polish", "Ukrainian", "Turkish", "Persian",
    "Hindi", "Bengali", "Indonesian", "Japanese", "Korean", "Swahili",
    "Thai", "Vietnamese", "Hebrew", "Greek", "Czech", "Swedish", "Norwegian",
    "Danish", "Finnish", "Hungarian", "Romanian"
]


def stable_int(seed: str, mod: int) -> int:
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(h[:12], 16) % mod


def clamp(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def make_population(country_name: str, iso_a3: str) -> int:
    # Детерминированное "население" 0.2M..250M
    base = stable_int(f"pop::{country_name}::{iso_a3}", 250_000_000)
    return 200_000 + base


def pick_languages(country_name: str, iso_a3: str) -> list[str]:
    """
    Выбираем 1..3 официальных языка детерминированно.
    """
    k = 1 + stable_int(f"k::{country_name}::{iso_a3}", 3)  # 1..3
    langs = []
    used = set()
    # делаем несколько "прыжков", чтобы получить разные языки
    for i in range(10):
        if len(langs) >= k:
            break
        idx = stable_int(f"lang::{country_name}::{iso_a3}::{i}", len(LANG_POOL))
        lang = LANG_POOL[idx]
        if lang not in used:
            used.add(lang)
            langs.append(lang)
    # на всякий случай
    if not langs:
        langs = [LANG_POOL[0]]
    return langs


def make_speakers_by_language(country_name: str, iso_a3: str, pop: int, langs: list[str]) -> dict[str, int]:
    """
    Детерминированно генерим "говорящих" по каждому официальному языку.
    ВАЖНО: чтобы не раздувать, ограничим сумму говорящих <= population
    (хотя билингвизм в реальности даёт пересечения).
    """
    # базовые "веса"
    weights = []
    for lang in langs:
        w = 10 + stable_int(f"w::{country_name}::{iso_a3}::{lang}", 90)  # 10..99
        weights.append(w)

    total_w = sum(weights) or 1
    # доля говорящих по всем офиц. языкам: 55%..98%
    pct_total = 55 + stable_int(f"pct_total::{country_name}::{iso_a3}", 44)  # 55..98
    total_speakers_budget = (pop * pct_total) // 100

    speakers = {}
    acc = 0
    for i, lang in enumerate(langs):
        if i == len(langs) - 1:
            val = total_speakers_budget - acc
        else:
            val = (total_speakers_budget * weights[i]) // total_w
            acc += val
        speakers[lang] = clamp(val, 0, pop)

    return speakers


def pick_code(p: dict, keys: list[str]) -> str:
    for k in keys:
        v = str(p.get(k) or "").strip()
        if v and v not in ("-99", "99"):
            return v
    return ""


def main():
    if not GEO_PATH.exists():
        raise FileNotFoundError(f"GeoJSON not found: {GEO_PATH}")

    with open(GEO_PATH, "r", encoding="utf-8") as f:
        geo = json.load(f)

    countries = {}
    missing_iso = 0

    for feat in geo.get("features", []):
        p = feat.get("properties", {}) or {}

        name = (p.get("ADMIN") or p.get("NAME_EN") or p.get("NAME") or "").strip()
        iso_a3 = pick_code(p, ["ADM0_A3", "ISO_A3", "SOV_A3", "WB_A3", "GU_A3", "SU_A3"])
        iso_a2 = pick_code(p, ["ISO_A2", "WB_A2"])

        if not name:
            continue

        if not iso_a3 or iso_a3 in ("-99", "99"):
            print(name)
            missing_iso += 1
            iso_a3 = f"X{hashlib.md5(name.encode('utf-8')).hexdigest()[:6].upper()}"

        if not iso_a2 or iso_a2 in ("-99", "99"):
            iso_a2 = ""

        pop = make_population(name, iso_a3)
        langs = pick_languages(name, iso_a3)
        speakers_by_lang = make_speakers_by_language(name, iso_a3, pop, langs)

        countries[iso_a3] = {
            "name": name,
            "iso_a3": iso_a3,
            "iso_a2": iso_a2,
            "official_languages": langs,
            "speakers_by_language": speakers_by_lang,
            "population": pop
        }

    OUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"schema_version": 3, "countries_by_iso_a3": countries},
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"Saved: {OUT_PATH}")
    print(f"Countries: {len(countries)} (missing ISO filled: {missing_iso})")


if __name__ == "__main__":
    main()
