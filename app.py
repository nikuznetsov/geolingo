import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "world_data.json"

app = FastAPI(title="World Languages Map (Natural Earth full coverage)")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[’'`]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_world_data() -> Dict[str, Any]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Missing {DATA_PATH}. Run: python scripts/generate_world_data.py"
        )
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "countries_by_iso_a3" not in data:
        raise ValueError("world_data.json has unexpected schema (missing countries_by_iso_a3).")
    return data


WORLD_DATA = load_world_data()
COUNTRIES: Dict[str, Dict[str, Any]] = WORLD_DATA["countries_by_iso_a3"]

# language_norm -> set(iso_a3)
LANG_TO_ISO3: Dict[str, Set[str]] = {}
for iso3, c in COUNTRIES.items():
    langs = c.get("official_languages") or []
    if isinstance(langs, str):
        langs = [langs]
    for lang in langs:
        if lang:
            LANG_TO_ISO3.setdefault(norm_text(lang), set()).add(iso3)


class CoverageRequest(BaseModel):
    languages: List[str] = Field(default_factory=list)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Все официальные языки всех стран
    all_langs: Set[str] = set()
    for c in COUNTRIES.values():
        langs = c.get("official_languages") or []
        if isinstance(langs, str):
            langs = [langs]
        for l in langs:
            if l:
                all_langs.add(l)

    known_languages = sorted(all_langs, key=lambda x: x.lower())

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "known_languages": known_languages},
    )


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    return FileResponse("sitemap.xml", media_type="application/xml")


@app.get("/robots.txt", include_in_schema=False)
def robots():
    return FileResponse("robots.txt", media_type="text/plain")


@app.get("/api/country_info")
def country_info():
    """
    Возвращает все страны по ISO_A3.
    """
    return {"countries_by_iso_a3": COUNTRIES}


@app.post("/api/coverage")
def coverage(payload: CoverageRequest):
    langs = [x.strip() for x in (payload.languages or []) if x and x.strip()]
    lang_norms = [norm_text(x) for x in langs]

    covered_iso3: Set[str] = set()
    unknown: List[str] = []

    for raw, ln in zip(langs, lang_norms):
        iso3s = LANG_TO_ISO3.get(ln)
        if iso3s:
            covered_iso3.update(iso3s)
        else:
            unknown.append(raw)

    covered_population = sum(int(COUNTRIES[i].get("population", 0)) for i in covered_iso3)

    # Суммарно говорящих по выбранным языкам в покрытых странах
    covered_speakers = 0
    for iso3 in covered_iso3:
        c = COUNTRIES.get(iso3, {})
        speakers_by_language = c.get("speakers_by_language") or {}
        # суммируем только по тем языкам, которые выбрал пользователь
        for raw in langs:
            covered_speakers += int(speakers_by_language.get(raw, 0))

    return {
        "input_languages": langs,
        "unknown_languages": unknown,
        "covered_iso_a3": sorted(covered_iso3),
        "covered_count": len(covered_iso3),
        "covered_population": covered_population,
        "covered_speakers_in_countries": covered_speakers,
    }

