from fractions import Fraction
from math import factorial
from settings import *
from src.simpleparitygame import SimpleParityGame
from src.simplestochasticgame import SimpleStochasticGame, SsgVertex, SsgTransition


def max_denom_and_min_prob(spg: SimpleParityGame, max_d: int=10_000) -> (float, int):
    floats = set()
    for transition in spg.transitions.values():
        for prob, vert in transition.end_vertices:
            floats.add(prob)
    fractions = [Fraction(f).limit_denominator(max_d) for f in floats]
    return (min(floats), max(fr.denominator for fr in fractions))

def compute_alphas_for_spg(spg: SimpleParityGame, max_d: int = 10_000):
    delta_min_float, max_denominator_M = max_denom_and_min_prob(spg, max_d)
    n_states = len(spg.vertices)
    used = sorted({v.priority for v in spg.vertices.values()})

    delta_min = Fraction(delta_min_float).limit_denominator(max_d)
    one_minus = Fraction(1, 1) - delta_min

    numerator   = delta_min ** n_states
    denominator = 8 * factorial(n_states) ** 2 * max_denominator_M ** (2 * n_states * n_states)
    alpha0 = float(numerator / denominator)    # Division einer Fraction durch int → Fraction

    ratio_bound = (one_minus * (delta_min ** n_states)) / (denominator + 1)

    alphas = { used[0]: alpha0 }
    for prev_k, next_k in zip(used, used[1:]):
        gap = next_k - prev_k
        alphas[next_k] = alphas[prev_k] * (ratio_bound ** gap)

    return alphas


def spg_to_ssg(spg: SimpleParityGame) -> SimpleStochasticGame:
    """
    Converts a SimpleParityGame to a SimpleStochasticGame.
    :param spg: The SimpleParityGame to convert
    :type spg: SimpleParityGame
    :return: The converted SimpleStochasticGame
    :rtype: SimpleStochasticGame
    """
    alphas = {0 : 0.5, 1 : 0.25}# compute_alphas_for_spg(spg)
    vertices: dict[str, SsgVertex] = dict()
    transitions: dict[tuple[SsgVertex, str], SsgTransition] = dict()
    initial_vertex: SsgVertex = None

    for v in spg.vertices.values():
        vertices[v.name] = SsgVertex(name=v.name, is_eve=v.is_eve, is_target=False)
    new_vertices: dict[str, SsgVertex] = dict()
    inital_vertex = vertices[spg.initial_vertex.name]
    respective_intermediate_vertices: dict[SsgVertex, SsgVertex] = dict()
    for v in spg.vertices.values():
        if not vertices.keys().__contains__(v.name+"\'"):
            new_vertices[v.name+"\'"] = SsgVertex(name=v.name+"\'", is_eve=v.is_eve, is_target=False)
            respective_intermediate_vertices[vertices[v.name]] = vertices[v.name+"\'"]
        else:
            i = 0
            while vertices.keys().__contains__(v.name+"\'"+str(i)):
                i += 1
            new_vertices[v.name+"\'"+str(i)] = SsgVertex(name=v.name+"\'"+str(i), is_eve=v.is_eve, is_target=False)
            respective_intermediate_vertices[vertices[v.name]] = vertices[v.name+"\'"+str(i)]
    vertices |= new_vertices
    if not vertices.keys().__contains__("v_win"):
        vertices["v_win"] = SsgVertex(name="v_win", is_eve=True, is_target=True)
    else:
        i=0
        while vertices.keys().__contains__("v_win"+str(i)):
            i += 1
        vertices["v_win"+str(i)] = SsgVertex(name="v_win"+str(i), is_eve=True, is_target=True)
    if not vertices.keys().__contains__("v_lose"):
        vertices["v_lose"] = SsgVertex(name="v_lose", is_eve=False, is_target=False)
    else:
        i=0
        while vertices.keys().__contains__("v_lose"+str(i)):
            i += 1
        vertices["v_lose"+str(i)] = SsgVertex(name="v_lose"+str(i), is_eve=False, is_target=False)

    for transition in spg.transitions.values():
        start_v = vertices[t.start_vertex]
        action = transition.action
        end_vs = set()
        for prob, end_v in transition.end_vertices:
            end_vs.add((prob, respective_intermediate_vertices[vertices[end_v.name]]))
        transitions[(start_v, action)] = SsgTransition(start_v, end_vs, action)

    for vertex in spg.vertices.values():
        if vertex.priority % 2 == 0:
            transitions[(respective_intermediate_vertices[vertex], "alpha")] = SsgTransition(respective_intermediate_vertices[vertex], "alpha", set((alphas[vertex.priority], vertices["v_win"]), (1-alphas[vertex.priority], vertices[vertex])))
        else:
            transitions[(respective_intermediate_vertices[vertex], "alpha")] = SsgTransition(respective_intermediate_vertices[vertex], "alpha", set((alphas[vertex.priority], vertices["v_lose"]), (1-alphas[vertex.priority], vertices[vertex])))

    return SimpleStochasticGame(spg, transitions, initial_vertex)



