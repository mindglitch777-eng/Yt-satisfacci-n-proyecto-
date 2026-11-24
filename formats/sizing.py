"""Tamaño de las bolitas (regla pedida por el usuario, vale para TODOS los formatos):
todas iguales y GRANDES mientras entren cómodas; recién cuando se aprietan se achican, de a poco.

r_objetivo(N) = clamp( R·sqrt(crowd / N), r_min, r_big )
  crowd = fracción del círculo que pueden ocupar antes de empezar a achicarse (0.40 ≈ cómodas).
El radio real persigue al objetivo suave (nunca salta) y solo se achica (nunca vuelve a crecer).
"""
import math


def target_r(n, R, r_big, r_min, crowd=0.30, r_mid=None, pack=0.78):
    """3 etapas (pedido del usuario): GRANDES al principio → se quedan en un tamaño MEDIANO mientras el círculo
    se va llenando → recién cuando ya no entran, se achican hasta quedar DIMINUTAS y el círculo queda tapado."""
    n = max(1, n)
    early = min(r_big, R * math.sqrt(crowd / n))
    if r_mid is None:
        return max(r_min, early)
    late = min(r_mid, R * math.sqrt(pack / n))
    return max(r_min, max(early, late) if early > r_mid else late)


def smooth_sizes(sim, n=None, rate=0.10):
    """llamar 1 vez por frame: acerca el radio de todas al objetivo del conteo actual."""
    if not sim.bodies:
        return
    n = len(sim.bodies) if n is None else n
    final_push = getattr(sim, "pending", None)
    tgt = sim.r_for(n)
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
