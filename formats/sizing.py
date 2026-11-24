"""Tamaño de las bolitas (regla pedida por el usuario, vale para TODOS los formatos):
todas iguales y GRANDES mientras entren cómodas; recién cuando se aprietan se achican, de a poco.

r_objetivo(N) = clamp( R·sqrt(crowd / N), r_min, r_big )
  crowd = fracción del círculo que pueden ocupar antes de empezar a achicarse (0.40 ≈ cómodas).
El radio real persigue al objetivo suave (nunca salta) y solo se achica (nunca vuelve a crecer).
"""
import math


def target_r(n, R, r_big, r_min, crowd=0.40):
    return max(r_min, min(r_big, R * math.sqrt(crowd / max(1, n))))


def smooth_sizes(sim, n=None, rate=0.10):
    """llamar 1 vez por frame: acerca el radio de todas al objetivo del conteo actual."""
    if not sim.bodies:
        return
    n = len(sim.bodies) if n is None else n
    tgt = target_r(n, sim.R, sim.r_big, sim.r_min, sim.g.get("crowd", 0.40))
    cur = sim.rad[0]
    if tgt >= cur - 0.02:
        return
    new = cur + (tgt - cur) * rate
    if abs(new - tgt) < 0.05:
        new = tgt
    for b in sim.bodies:
        for sh in b.shapes:
            sh.unsafe_set_radius(new)
    sim.rad = [new] * len(sim.bodies)
