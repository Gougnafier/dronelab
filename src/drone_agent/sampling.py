"""Tirage aléatoire de paramètres dans les bornes d'une spec.

Convention des bornes : [min, max] numériques -> intervalle (entier si les deux bornes sont
entières) ; toute autre liste -> choix parmi les valeurs.
"""

from __future__ import annotations

import random


def is_interval(values: list) -> bool:
    return (len(values) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values)
            and values[0] < values[1])


def sample_params(bounds: dict, rng: random.Random) -> dict:
    params = {}
    for key, values in bounds.items():
        if not is_interval(values):
            params[key] = rng.choice(values)
        elif all(isinstance(v, int) for v in values):
            params[key] = rng.randint(values[0], values[1])
        else:
            params[key] = round(rng.uniform(float(values[0]), float(values[1])), 2)
    return params
