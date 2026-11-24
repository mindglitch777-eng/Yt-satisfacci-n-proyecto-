"""Compara el movimiento de un render contra la referencia medida. Sale con código 1 si algo está fuera de tolerancia.

    python -m tools.motion.compare reference/formats/punch/target.json render_medido.json
(render_medido.json = salida de `python -m tools.motion.measure mi_video.mp4 -o render_medido.json`)
"""
import json, sys

# (clave, tolerancia relativa o absoluta, explicación cuando falla)
CHECKS = [
    ("clap_interval_early_s", .25, "ritmo de golpes al principio"),
    ("clap_interval_late_s", .25, "ritmo de golpes al final (tiene que ser más lento que al principio)"),
    ("clap_hold_s", .4, "cuánto tiempo quedan los guantes juntos en el golpe"),
    ("arm_velocity_corr", ("abs", .2), "relación entre brazos: negativa = tijera/aplauso simétrico"),
    ("arm_mean_speed_deg_s", .25, "velocidad media de los brazos"),
    ("ball_r_over_R_first", .3, "tamaño de la primera bola (grande y legible en el frame 1)"),
    ("ball_r_over_R_last", .6, "tamaño de bola al final"),
    ("mass_in_top_half_pct", ("abs", 15), "gravedad efectiva (50% = sin gravedad real, ~0% = todo abajo)"),
]


# pinzas laterales (crusher_jaws): las métricas de brazos centrales no aplican; valen estas
CHECKS_JAWS = [
    ("machine_period_s", .25, "ritmo general de la máquina"),
    ("jaw_cycle_s", .2, "tiempo entre entradas de pinza"),
    ("jaw_alternation", ("abs", .15), "las pinzas se alternan izquierda/derecha"),
    ("jaw_reach", .2, "cuánto entra la pinza hacia el centro"),
    ("jaw_in_s", .35, "velocidad de entrada de la pinza"),
    ("jaw_active_s", .25, "cuánto tiempo está adentro cada pinza"),
    ("jaw_overlap_pct", ("abs", 10), "las dos pinzas casi nunca están adentro a la vez"),
    ("jaw_outside_pct", ("abs", 15), "los brazos salen AFUERA del aro al abrirse (giran alrededor del engranaje)"),
    ("ball_r_over_R_first", .3, "tamaño de la primera bola"),
    ("ball_r_over_R_last", .6, "tamaño de bola al final"),
    ("mass_in_top_half_pct", ("abs", 15), "gravedad efectiva (sin gravedad ≈ 50-65%)"),
]


def main(ref_p, got_p):
    ref = json.load(open(ref_p)); ref = ref.get("summary", ref)
    got = json.load(open(got_p)); got = got.get("summary", got)
    bad = 0
    checks = CHECKS_JAWS if ref.get("machine") == "jaws" else CHECKS
    print(f"{'métrica':32} {'ref':>8} {'render':>8}  estado")
    for k, tol, why in checks:
        r, g = ref.get(k), got.get(k)
        if r is None or g is None:
            print(f"{k:32} {str(r):>8} {str(g):>8}  ? sin dato"); continue
        ok = abs(g - r) <= tol[1] if isinstance(tol, tuple) else abs(g - r) <= abs(r) * tol
        bad += not ok
        print(f"{k:32} {r:>8} {g:>8}  {'OK' if ok else 'FUERA → ' + why}")
    am = got.get("arm_moving_pct") or [0, 0]
    if checks is CHECKS and min(am) < 30:
        bad += 1; print(f"{'arm_moving_pct':32} {str(ref.get('arm_moving_pct')):>8} {str(am):>8}  FUERA → los DOS brazos se mueven")
    print("\nRESULTADO:", "PASA" if not bad else f"{bad} métricas fuera de tolerancia")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
