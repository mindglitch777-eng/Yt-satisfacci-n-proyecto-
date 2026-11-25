"""Pacer: el clímax se programa, nunca queda librado al azar.

desired(t) sigue una curva exponencial que llega a la capacidad justo en `target_t`.
Además guiona la batalla: quién lidera en cada tramo, cambios de líder y un near-miss
(el segundo queda a centímetros) poco antes del clímax.
"""
import math


class Pacer:
    def __init__(self, target_t, cap, curve, n_teams, winner, rng):
        self.T, self.cap, self.k = target_t, cap, curve
        self.n, self.winner = n_teams, winner
        # guion de liderazgo: (hasta_frac_del_tiempo, líder). Siempre termina ganando `winner`.
        others = [i for i in range(n_teams) if i != winner]
        rng.shuffle(others)
        swaps = [(0.30, others[0]), (0.55, winner), (0.78, others[-1])]
        self.script = swaps + [(1.01, winner)]
        self.near_miss_t = target_t * rng.uniform(0.86, 0.92)   # el rival casi alcanza
        self.rival = others[-1]

    def desired(self, t):
        x = min(1.0, max(0.0, t / self.T))
        return self.cap * (math.exp(self.k * x) - 1) / (math.exp(self.k) - 1)

    def leader(self, t):
        x = t / self.T
        for until, who in self.script:
            if x < until:
                return who
        return self.winner

    def shares(self, t):
        """participación objetivo de cada equipo (suma 1)."""
        lead = self.leader(t)
        base = [1.0] * self.n
        base[lead] = 1.35
        # near-miss: rival pegado al ganador un instante
        if abs(t - self.near_miss_t) < 1.5:
            base = [1.0] * self.n
            base[self.winner], base[self.rival] = 1.25, 1.23
        if t > self.T * 0.94:
            base[self.winner] = 1.5
        s = sum(base)
        return [b / s for b in base]

    def spawn(self, t, team, counts, base_mult):
        """cuántas fichas nuevas genera un golpe a una ficha de `team`."""
        total = sum(counts)
        d = self.desired(t)
        want = d * self.shares(t)[team]
        have = counts[team]
        if total >= self.cap or have > want * 1.12:
            return 0
        if have < want * 0.75:
            return base_mult + 2
        return base_mult
