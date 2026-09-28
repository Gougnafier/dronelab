"""Cas de charge CalculiX : écriture du fichier .inp, exécution bornée, lecture du .dat.

Unités cohérentes : mm, N, t (tonne), s -> MPa, Hz.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

G_MM_S2 = 9810.0
STATIC_CASES = ("max_thrust", "motor_torque", "maneuver", "crash")


def ccx_executable() -> str:
    found = os.environ.get("CCX") or shutil.which("ccx")
    if not found:
        env_bin = Path(os.sys.executable).parent / "ccx"
        if env_bin.exists():
            return str(env_bin)
        raise FileNotFoundError("exécutable CalculiX « ccx » introuvable")
    return found


def material_block(material: dict) -> str:
    rho_t_mm3 = material["density_g_cm3"] * 1e-9
    return (
        "*MATERIAL, NAME=MAT\n*ELASTIC\n"
        f"{material['young_mpa']}, {material['poisson']}\n"
        f"*DENSITY\n{rho_t_mm3:.6e}\n"
        "*SOLID SECTION, ELSET=EALL, MATERIAL=MAT\n"
    )


def case_deck(case: str, spec: dict, material: dict, mesh_info: dict) -> str:
    """Fichier d'entrée complet pour un cas ; le maillage est inclus depuis ../mesh.inp."""
    ref, rot, mass_elem = mesh_info["max_node_id"] + 1, mesh_info["max_node_id"] + 2, mesh_info["elements"] + 1
    x, y, z = mesh_info["motor_ref_xyz"]
    motor_mass_t = spec["drone"]["motor_mass_g"] * 1e-6
    deck = [
        "*INCLUDE, INPUT=../mesh.inp",
        material_block(material).rstrip(),
        f"*NODE, NSET=NREF\n{ref}, {x}, {y}, {z}\n{rot}, {x}, {y}, {z}",
        f"*RIGID BODY, NSET=NMOTOR, REF NODE={ref}, ROT NODE={rot}",
        "*BOUNDARY\nNROOT, 1, 3",
    ]
    lc = spec["load_cases"]
    if case == "modal":
        deck += [
            f"*ELEMENT, TYPE=MASS, ELSET=EMOTOR\n{mass_elem}, {ref}",
            f"*MASS, ELSET=EMOTOR\n{motor_mass_t:.6e}",
            f"*STEP\n*FREQUENCY\n{int(lc['modal']['modes'])}",
            "*END STEP",
        ]
        return "\n".join(deck) + "\n"

    loads = []
    if case in ("max_thrust", "crash"):
        for dof, value in enumerate(lc[case]["force_n"], start=1):
            if value:
                loads.append(f"{ref}, {dof}, {value}")
    elif case == "motor_torque":
        for dof, value in enumerate(lc[case]["moment_nm"], start=1):
            if value:
                loads.append(f"{rot}, {dof}, {value * 1000.0}")
    elif case == "maneuver":
        n = lc[case]["load_factor"]
        loads.append(f"{ref}, 3, {-n * motor_mass_t * G_MM_S2:.6f}")
    else:
        raise ValueError(f"cas de charge inconnu : {case}")

    deck += ["*STEP", "*STATIC", "*CLOAD", *loads]
    if case == "maneuver":
        deck += ["*DLOAD", f"EALL, GRAV, {lc[case]['load_factor'] * G_MM_S2}, 0., 0., -1."]
    deck += [
        "*NODE PRINT, NSET=NREF", "U",
        "*NODE PRINT, NSET=NALL, TOTALS=NO", "U",
        "*EL PRINT, ELSET=EEVAL", "S",
        "*NODE FILE", "U",
        "*EL FILE", "S",
        "*END STEP",
    ]
    return "\n".join(deck) + "\n"


def run_ccx(case_dir: Path, job: str, timeout_s: float, threads: int) -> dict:
    env = {**os.environ, "OMP_NUM_THREADS": str(threads), "CCX_NPROC_EQUATION_SOLVER": str(threads)}
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [ccx_executable(), "-i", job], cwd=case_dir, env=env,
            capture_output=True, text=True, timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": f"timeout après {timeout_s:.0f} s", "seconds": timeout_s}
    seconds = round(time.monotonic() - start, 2)
    (case_dir / f"{job}.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    errors = [line.strip() for line in (proc.stdout + proc.stderr).splitlines() if "*ERROR" in line]
    if proc.returncode != 0 or errors:
        return {"ok": False, "reason": "; ".join(errors[:3]) or f"ccx code {proc.returncode}", "seconds": seconds}
    return {"ok": True, "seconds": seconds}


_BLOCK = re.compile(r"^\s*(displacements|stresses)\b.*?for set (\S+)", re.IGNORECASE)


def parse_static_dat(path: Path) -> dict:
    """Déplacements par ensemble et contrainte de von Mises max sur EEVAL."""
    displacements: dict[str, dict[int, tuple[float, float, float]]] = {}
    vm_max, vm_elem = 0.0, None
    current, current_set = None, None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _BLOCK.match(line)
        if match:
            current, current_set = match.group(1).lower(), match.group(2).upper()
            if current == "displacements":
                displacements.setdefault(current_set, {})
            continue
        parts = line.split()
        if parts and parts[-1].startswith("_"):  # étiquette des coques développées (« _shell_… »)
            parts = parts[:-1]
        if not parts or current is None:
            continue
        try:
            values = [float(v) for v in parts]
        except ValueError:
            current = None
            continue
        if current == "displacements" and len(values) == 4:
            displacements[current_set][int(values[0])] = tuple(values[1:4])
        elif current == "stresses" and len(values) == 8:
            sxx, syy, szz, sxy, sxz, syz = values[2:8]
            vm = math.sqrt(
                0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                + 3.0 * (sxy**2 + sxz**2 + syz**2)
            )
            if vm > vm_max:
                vm_max, vm_elem = vm, int(values[0])
    return {"displacements": displacements, "von_mises_max_mpa": vm_max, "von_mises_elem": vm_elem}


def parse_frequencies(path: Path) -> list[float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    marker = text.find("E I G E N V A L U E   O U T P U T")
    if marker < 0:
        return []
    freqs = []
    for line in text[marker:].splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 4 and parts[0].isdigit():
            eigenvalue = float(parts[1])
            freqs.append(math.sqrt(max(eigenvalue, 0.0)) / (2 * math.pi))
        elif freqs and not parts:
            break
    return freqs
