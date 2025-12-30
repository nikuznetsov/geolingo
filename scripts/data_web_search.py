import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PROMPT = """You must answer STRICTLY with a single valid JSON object.

Do NOT include:
- markdown
- explanations
- comments
- trailing commas

The response must start with { and end with }.

Task:
- List the official languages recognized at the national/state level in the given country.
- For each official language, provide the number of people who speak that language in that country.
- Provide the total population of that country.

If there is no exact number for language speakers, 
use average number for ranges and if percent calculate it from population.

Output format:
{
  "official_languages": ["English"],
  "speakers_by_language": {
    "English": 12345678
  },
  "population": 98765432
}
"""


def ask_official_languages(client: OpenAI, country_name: str) -> Dict[str, Any]:
    """
    Calls the model with web_search tool and returns a dict:
      { official_languages: [...], speakers_by_language: {...}, population: int }
    """
    resp = client.responses.create(
        model="gpt-5.2",
        temperature=0,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a careful data analyst. "
                    "Return ONLY valid JSON. No markdown, no comments."
                ),
            },
            {
                "role": "user",
                "content": f"{PROMPT}\n\nCountry: {country_name}",
            },
        ],
        tools=[
            {
                "type": "web_search",
                "search_context_size": "high"
            }
        ],
        tool_choice={
            "type": "web_search"
        }
    )

    text = resp.output_text.strip()

    data = json.loads(text)

    # Minimal schema validation / normalization
    if not isinstance(data, dict):
        raise ValueError("Model returned non-object JSON")

    if "official_languages" not in data or "speakers_by_language" not in data or "population" not in data:
        raise ValueError(f"Missing required keys in model output: {data.keys()}")

    if not isinstance(data["official_languages"], list):
        raise ValueError("official_languages must be a list")

    if not isinstance(data["speakers_by_language"], dict):
        raise ValueError("speakers_by_language must be a dict")

    if not isinstance(data["population"], int):
        # allow numeric strings
        try:
            data["population"] = int(data["population"])
        except Exception:
            raise ValueError("population must be an int")

    # Ensure all speakers values are ints
    speakers_norm = {}
    for k, v in data["speakers_by_language"].items():
        try:
            speakers_norm[str(k)] = int(v)
        except Exception:
            speakers_norm[str(k)] = 0
    data["speakers_by_language"] = speakers_norm

    # Ensure languages are strings, unique, and match speakers keys if possible
    langs = []
    seen = set()
    for l in data["official_languages"]:
        ls = str(l).strip()
        if ls and ls.lower() not in seen:
            langs.append(ls)
            seen.add(ls.lower())
    data["official_languages"] = langs

    return data


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def update_country_record(country_rec: Dict[str, Any], result: Dict[str, Any]) -> None:
    """
    Mutates country_rec in place, overwriting:
      official_languages, speakers_by_language, population
    """
    country_rec["official_languages"] = result["official_languages"]
    country_rec["speakers_by_language"] = result["speakers_by_language"]
    country_rec["population"] = result["population"]


def should_skip_already_filled(country_rec: Dict[str, Any]) -> bool:
    """
    Optional: skip if looks already 'rich'.
    Adjust this if you want to ALWAYS overwrite.
    """
    langs = country_rec.get("official_languages")
    spk = country_rec.get("speakers_by_language")
    pop = country_rec.get("population")
    return isinstance(langs, list) and isinstance(spk, dict) and isinstance(pop, int) and pop > 0 and len(langs) > 0


def main(
    input_path: str = "data/world_data.json",
    output_path: str = "data/world_data_rich.json",
    overwrite: bool = True,
    sleep_seconds: float = 0.4,
    checkpoint_every: int = 10,
) -> None:
    input_path = str(input_path)
    output_path = str(output_path)

    in_path = Path(input_path)
    out_path = Path(output_path)

    world = load_json(in_path)

    if "countries_by_iso_a3" not in world or not isinstance(world["countries_by_iso_a3"], dict):
        raise ValueError("world_data.json must contain countries_by_iso_a3 dict")

    countries = world["countries_by_iso_a3"]

    # If output exists, resume from it (so you can stop/restart safely)
    if out_path.exists():
        print(f"Found existing {out_path}, resuming from it.")
        world_out = load_json(out_path)
        if "countries_by_iso_a3" in world_out and isinstance(world_out["countries_by_iso_a3"], dict):
            countries_out = world_out["countries_by_iso_a3"]
            # merge base world into output (keep any previous enrichments)
            for iso3, rec in countries.items():
                if iso3 not in countries_out:
                    countries_out[iso3] = rec
            world = world_out
            countries = countries_out
        else:
            print("Existing output has unexpected schema; starting from input instead.")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    items = list(countries.items())
    total = len(items)
    updated = 0
    skipped = 0
    failed = 0

    for idx, (iso3, rec) in enumerate(items, start=1):
        name = rec.get("name") or iso3

        if not overwrite and should_skip_already_filled(rec):
            skipped += 1
            print(f"[{idx}/{total}] SKIP (already filled): {name} ({iso3})")
            continue

        print(f"[{idx}/{total}] FETCH: {name} ({iso3})")
        try:
            result = ask_official_languages(client, name)
            update_country_record(rec, result)
            updated += 1
        except Exception as e:
            failed += 1
            rec.setdefault("_enrich_error", str(e))
            print(f"  ERROR: {name}: {e}")

        # checkpoint save
        if (idx % checkpoint_every) == 0:
            save_json(out_path, world)
            print(f"  ✅ checkpoint saved to {out_path}")

        time.sleep(sleep_seconds)

    save_json(out_path, world)
    print("\nDone.")
    print(f"Updated: {updated}, Skipped: {skipped}, Failed: {failed}")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main(
        input_path="data/world_data.json",
        output_path="data/world_data_rich.json",
        overwrite=True,        # ставь False, если хочешь не трогать уже заполненные
        sleep_seconds=0.4,      # увеличь, если будут rate-limit ошибки
        checkpoint_every=10,    # сохранять прогресс каждые N стран
    )
