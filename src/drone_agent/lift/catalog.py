"""Catalogue des pièces achetées : chaque entrée vient d'une source précise, vérifiée à l'ajout.

Les masses des pièces du commerce utilisées dans un assemblage viennent d'ici, jamais d'une déclaration libre.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from ..store import append_jsonl, now_iso, read_jsonl
from .exam import exam_spec

REQUIRED = {
    "motor": ["mass_kg", "max_continuous_power_w", "diameter_m", "height_m", "mount_pattern_mm"],
    "propeller": ["mass_kg", "diameter_m"],
    "battery": ["mass_kg", "energy_wh", "max_continuous_power_w", "dims_m"],
    "esc": ["mass_kg", "max_continuous_power_w", "dims_m"],
    "tube": ["mass_per_m_kg", "outer_diameter_m", "wall_m", "material"],
    "avionics": ["mass_kg", "dims_m"],
    "wiring": ["mass_per_m_kg"],
    "landing_gear": ["mass_kg", "dims_m"],
    "other": ["mass_kg", "dims_m"],
}
TUBE_DENSITY = {"CFRP": (1300, 2000), "AL": (2600, 2900)}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def check_url(url: str, timeout: float = 12.0) -> dict:
    """Ouvre la page citée. 404/410/erreur réseau = refus ; 401/403/429 = accessible mais non lisible."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return {"reachable": False, "status": None, "reason": "URL invalide"}
    if parsed.path in ("", "/") and not parsed.query:
        return {"reachable": False, "status": None, "reason": "page d'accueil : citer la fiche produit précise"}
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (dronelab catalog check)"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(600_000).decode("utf-8", errors="replace")
            return {"reachable": True, "status": response.status, "text": body}
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403, 405, 429, 503):
            return {"reachable": True, "status": exc.code, "text": "", "reason": "accès refusé aux robots : contenu non vérifié"}
        return {"reachable": False, "status": exc.code, "reason": f"HTTP {exc.code}"}
    except Exception as exc:  # DNS, délai, TLS
        return {"reachable": False, "status": None, "reason": f"{type(exc).__name__}: {exc}"[:200]}


def validate(category: str, specs: dict) -> list[str]:
    spec = exam_spec()
    issues = []
    if category not in REQUIRED:
        return [f"catégorie inconnue : {category} (disponibles : {sorted(REQUIRED)})"]
    for key in REQUIRED[category]:
        if key not in specs:
            issues.append(f"spécification manquante : {key}")
    if issues:
        return issues
    num = {k: v for k, v in specs.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    if any(v <= 0 for k, v in num.items() if k.endswith(("_kg", "_w", "_wh", "_m"))):
        issues.append("valeurs de masse, puissance, énergie et dimensions strictement positives")
    plaus, floors = spec["plausibility"], spec["mass_floors"]
    if category == "motor" and specs.get("peak_power_w") is not None and specs["peak_power_w"] < specs["max_continuous_power_w"]:
        issues.append("peak_power_w (puissance de pointe) doit être ≥ max_continuous_power_w")
    if category == "motor" and specs["max_continuous_power_w"] / specs["mass_kg"] > plaus["motor_specific_power_max_w_kg"]:
        issues.append(f"puissance massique {specs['max_continuous_power_w'] / specs['mass_kg']:.0f} W/kg > "
                      f"{plaus['motor_specific_power_max_w_kg']} W/kg (puissance continue, pas crête)")
    if category == "battery":
        wh_kg = specs["energy_wh"] / specs["mass_kg"]
        c_rate = specs["max_continuous_power_w"] / specs["energy_wh"]
        tier = next((t for t in plaus["battery_tiers"] if wh_kg <= t["max_wh_kg"]), None)
        if tier is None:
            issues.append(f"{wh_kg:.0f} Wh/kg au niveau du pack : au-delà des paliers de l'épreuve")
        elif c_rate > tier["max_c"]:
            issues.append(f"{c_rate:.1f} C > {tier['max_c']} C pour {wh_kg:.0f} Wh/kg")
    if category == "esc" and specs["mass_kg"] < floors["esc_kg_per_kw"] * specs["max_continuous_power_w"] / 1000:
        issues.append("variateur plus léger que le minimum de l'épreuve pour sa puissance")
    if category == "propeller":
        minimum = floors["prop_kg_at_1m"] * specs["diameter_m"] ** floors["prop_exponent"]
        if specs["mass_kg"] < minimum:
            issues.append(f"hélice de {specs['diameter_m']} m plus légère que {minimum:.2f} kg")
    if category == "tube":
        od, wall = specs["outer_diameter_m"], specs["wall_m"]
        if wall * 2 >= od:
            issues.append("paroi ≥ rayon")
        else:
            area = 3.14159265 / 4 * (od**2 - (od - 2 * wall) ** 2)
            density = specs["mass_per_m_kg"] / area
            lo, hi = TUBE_DENSITY.get(str(specs["material"]).upper(), (1000, 3000))
            if not lo <= density <= hi:
                issues.append(f"masse linéique incohérente : densité apparente {density:.0f} kg/m³ pour {specs['material']}")
    if "dims_m" in specs and (not isinstance(specs["dims_m"], list) or len(specs["dims_m"]) != 3):
        issues.append("dims_m : [longueur, largeur, hauteur] en mètres")
    return issues


def add(root: Path, category: str, name: str, manufacturer: str, specs: dict, source_url: str,
        source_excerpt: str, url_checker=check_url) -> dict:
    issues = validate(category, specs)
    if len(source_excerpt.strip()) < 20:
        issues.append("extrait de la source trop court (20 caractères min) : citer la ligne de la fiche")
    page = url_checker(source_url)
    if not page.get("reachable"):
        issues.append(f"source inaccessible : {page.get('reason')}")
    if issues:
        return {"ok": False, "issues": issues}
    numbers = re.findall(r"\d+(?:[.,]\d+)?", source_excerpt)
    text = page.get("text", "")
    found = [n for n in numbers if n in text] if text else []
    entry = {"id": f"{category}:{_slug(manufacturer + '-' + name)}", "category": category, "name": name,
             "manufacturer": manufacturer, "specs": specs, "source_url": source_url, "source_excerpt": source_excerpt,
             "source_status": page.get("status"), "excerpt_numbers_found_on_page": f"{len(found)}/{len(numbers)}",
             "source_note": page.get("reason", ""), "added_at": now_iso()}
    root.mkdir(parents=True, exist_ok=True)
    append_jsonl(root / "catalog.jsonl", entry)
    return {"ok": True, "entry": entry}


def entries(root: Path) -> dict[str, dict]:
    latest = {}
    for row in read_jsonl(root / "catalog.jsonl"):
        latest[row["id"]] = row
    return latest


def search(root: Path, category: str | None, text: str | None) -> list[dict]:
    rows = entries(root).values()
    if category:
        rows = [r for r in rows if r["category"] == category]
    if text:
        rows = [r for r in rows if text.lower() in json.dumps(r, ensure_ascii=False).lower()]
    return list(rows)
