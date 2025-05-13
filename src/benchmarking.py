import random
from settings import *
from simplestochasticgame import *


def create_random_ssgs(number_of_ssgs: int, number_of_vertices: int, number_of_transitions: int, number_of_target_vertices: int) -> list:
    """
    Create a list of new SSGs with random parameters.
    :param number_of_ssgs: Number of SSGs to create
    :type number_of_ssgs: int
    :param number_of_vertices: Maximum number of vertices in the SSG
    :type number_of_vertices: int
    :param number_of_transitions: Maximum number of transitions in the SSG
    :type number_of_transitions: int
    :param number_of_target_vertices: Maximum number of target vertices in the SSG
    :type number_of_target_vertices: int
    :return: List of new random SSGs
    :rtype: list
    """
    ssgs = []
    for _ in range(number_of_ssgs):
        vertices: dict[str, SsgVertex] = dict()
        for i in range(number_of_vertices):
            vertices[f"vertex_{i}"] = SsgVertex(f"vertex_{i}", bool(random.randint(0, 1)), False)
        target_vertices = random.sample(list(vertices.values()), number_of_target_vertices)
        for vertex in target_vertices:
            vertex.is_target = True
        init_vertex = random.choice(list(vertices.values()))
        transitions: dict[(SsgVertex, str), SsgTransition] = dict()
        action = 0
        for i in range(number_of_transitions):
            start_vertex = random.choice(list(vertices.values()))
            type_of_transition = random.choice([0, 1])
            if type_of_transition == 0:
                end_vertex = random.choice(list(vertices.values()))
                transitions[(start_vertex, str(action))] = SsgTransition(start_vertex, {(1.0, end_vertex)}, str(action))
            else:
                end_vertices = random.sample(list(vertices.values()), 2)
                transitions[(start_vertex, str(action))] = SsgTransition(start_vertex, {(0.5, end_vertices[0]), (0.5, end_vertices[1])}, str(action))
        ssg = SimpleStochasticGame(vertices, transitions, init_vertex)
        ssgs.append(ssg)
    return ssgs


list_of_ssgs = create_random_ssgs(10, 1000, 10000, 10)
