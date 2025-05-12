from fractions import Fraction
from math import factorial
from simpleparitygame import *
from simplestochasticgame import *



def max_denom_and_min_prob(spg: SimpleParityGame, max_d: int=10_000) -> (float, int):
    floats = set()
    for transition in spg.transitions.values():
        for prob, vert in transition.end_vertices:
            floats.add(prob)
    fractions = [Fraction(f).limit_denominator(max_d) for f in floats]
    return (min(floats), max(fr.denominator for fr in fractions))

def compute_alphas_for_spg(spg: SimpleParityGame, max_d: int = 10_000):
    # ... delta_min_float, max_denominator_M, n_states, used wie vorher ...
    delta_min_float, max_denominator_M = max_denom_and_min_prob(spg, max_d)
    n_states = 10 #len(spg.vertices)
    used = sorted({v.priority for v in spg.vertices.values()})

    delta_min = Fraction(delta_min_float).limit_denominator(max_d)
    one_minus = Fraction(1, 1) - delta_min

    # 2) α0 = delta_min**n / (8 * (n!)² * M^(2 n²))
    numerator   = delta_min ** n_states
    denominator = 8 * factorial(n_states) ** 2 * max_denominator_M ** (2 * n_states * n_states)
    alpha0 = float(numerator / denominator)    # Division einer Fraction durch int → Fraction

    # 3) ratio_bound = (1−δ)·δⁿ  / (8·(n!)²·M^(2n²) + 1)
    ratio_bound = (one_minus * (delta_min ** n_states)) / (denominator + 1)

    # 4) über Lücken hinweg aufbauen
    alphas = { used[0]: alpha0 }
    for prev_k, next_k in zip(used, used[1:]):
        gap = next_k - prev_k
        alphas[next_k] = alphas[prev_k] * (ratio_bound ** gap)

    return alphas


