from fractions import Fraction
from math import factorial
from settings import *
from src.simpleparitygame import SimpleParityGame, read_spg_from_file
from src.simplestochasticgame import SimpleStochasticGame, SsgVertex, SsgTransition


def max_denom_and_min_prob(spg: SimpleParityGame, max_d: int=10_000) -> (float, int):
    floats = set()
    for transition in spg.transitions.values():
        for prob, vert in transition.end_vertices:
            floats.add(prob)
    fractions = [Fraction(f).limit_denominator(max_d) for f in floats]
    return (min(floats), max(fr.denominator for fr in fractions))

def compute_alphas_for_spg(spg: SimpleParityGame, epsilon: float = None, max_d: int = 10_000):

    delta_min_float, max_denominator_M = max_denom_and_min_prob(spg, max_d)
    n_states = len(spg.vertices)
    used = sorted({v.priority for v in spg.vertices.values()})

    delta_min = Fraction(delta_min_float).limit_denominator(max_d)
    one_minus = Fraction(1, 1) - delta_min
    if epsilon is None:
        numerator   = delta_min ** n_states
        denominator = 8 * factorial(n_states) ** 2 * max_denominator_M ** (2 * n_states * n_states)
        alpha0 = float(numerator / denominator)

        ratio_bound = (one_minus * (delta_min ** n_states)) / (denominator + 1)

        alphas = { used[0]: alpha0 }
        for prev_k, next_k in zip(used, used[1:]):
            gap = next_k - prev_k
            alphas[next_k] = alphas[prev_k] * (ratio_bound ** gap)
    else:
        numerator = 4 * epsilon * delta_min ** n_states
        denominator = (4 - epsilon) * delta_min
        alpha0 = float(numerator / denominator)

        ratio_bound = (one_minus * (delta_min ** n_states)) / (((8 * (4 - epsilon)) / (4 * epsilon)) + 1)
        alphas = { used[0]: alpha0 }
        for prev_k, next_k in zip(used, used[1:]):
            gap = next_k - prev_k
            alphas[next_k] = alphas[prev_k] * (ratio_bound ** gap)
    return alphas


def spg_to_ssg(spg: SimpleParityGame, epsilon: float = None) -> SimpleStochasticGame:
    """
    Converts a SimpleParityGame to a SimpleStochasticGame.
    :param spg: The SimpleParityGame to convert
    :type spg: SimpleParityGame
    :return: The converted SimpleStochasticGame
    :rtype: SimpleStochasticGame
    """
    alphas = compute_alphas_for_spg(spg, epsilon=epsilon)
    vertices: dict[str, SsgVertex] = dict()
    transitions: dict[tuple[SsgVertex, str], SsgTransition] = dict()
    respective_spg_ssg_vertixes: dict[SpgVertex, SsgVertex] = dict()
    initial_vertex: SsgVertex = None

    for v in spg.vertices.values():
        vertices[v.name] = SsgVertex(name=v.name, is_eve=v.is_eve, is_target=False)
        respective_spg_ssg_vertixes[v] = vertices[v.name]
    new_vertices: dict[str, SsgVertex] = dict()
    initial_vertex = vertices[spg.init_vertex.name]
    respective_intermediate_vertices: dict[SsgVertex, SsgVertex] = dict()
    for v in spg.vertices.values():
        if not vertices.keys().__contains__(v.name+"\'"):
            new_vertices[v.name+"\'"] = SsgVertex(name=v.name+"\'", is_eve=v.is_eve, is_target=False)
            respective_intermediate_vertices[vertices[v.name]] = new_vertices[v.name+"\'"]
        else:
            i = 0
            while vertices.keys().__contains__(v.name+"\'"+str(i)):
                i += 1
            new_vertices[v.name+"\'"+str(i)] = SsgVertex(name=v.name+"\'"+str(i), is_eve=v.is_eve, is_target=False)
            respective_intermediate_vertices[vertices[v.name]] = new_vertices[v.name+"\'"+str(i)]
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
        start_v = vertices[transition.start_vertex.name]
        action = transition.action
        end_vs = set()
        for prob, end_v in transition.end_vertices:
            end_vs.add((prob, respective_intermediate_vertices[vertices[end_v.name]]))
        transitions[(start_v, action)] = SsgTransition(start_v, end_vs, action)

    for vertex in spg.vertices.values():
        if vertex.priority % 2 == 0:
            transitions[(respective_intermediate_vertices[respective_spg_ssg_vertixes[vertex]], "alpha")] = SsgTransition(respective_intermediate_vertices[respective_spg_ssg_vertixes[vertex]], {(alphas[vertex.priority], vertices["v_win"]), (1-alphas[vertex.priority], vertices[respective_spg_ssg_vertixes[vertex].name])}, "alpha")
        else:
            transitions[(respective_intermediate_vertices[respective_spg_ssg_vertixes[vertex]], "alpha")] = SsgTransition(respective_intermediate_vertices[respective_spg_ssg_vertixes[vertex]], {(alphas[vertex.priority], vertices["v_lose"]), (1-alphas[vertex.priority], vertices[respective_spg_ssg_vertixes[vertex].name])}, "alpha")
    return SimpleStochasticGame(vertices, transitions, initial_vertex)



spg = read_spg_from_file("test_1.spg", use_global_path=True)
ssg = spg_to_ssg(spg, epsilon=1e-100)
from ssg_to_smg import ssg_to_smgspec, save_smg_file, check_target_reachability
smgspec = ssg_to_smgspec(ssg)
save_smg_file(smgspec, "test_1.smg", use_global_path=True, force=True)
check_target_reachability("test_1.smg", use_global_path=True, print_probabilities=True, debug=True)
