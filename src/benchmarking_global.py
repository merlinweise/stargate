# Imports
import queue as pyqueue
import random
import time
import json
import os
import psutil

from pympler import asizeof
from multiprocessing import Process, Manager

from ssg_to_smg import check_target_reachability
from stochasticparitygame import SpgVertex, SpgTransition, StochasticParityGame, read_spg_from_file
from error_handling import print_error, print_debug, print_warning
from spg_to_ssg_reduction import spg_to_ssg
from ssg_to_smg import ssg_to_smgspec, save_smg_file, check_property
from settings import GLOBAL_DEBUG, MAX_ITERS, PRISM_PATH, PRISM_EPSILON, GLOBAL_IN_OUT_PATH


def create_chain_spg(length: int, min_prob: float) -> StochasticParityGame:
    """
    Creates a chain Stochastic Parity Game with a given length and minimum probability for the transitions.
    :param length: Length of the chain in number of vertices (not including the end vertex)
    :type length: int
    :param min_prob: Probability of the transition to the next vertex, must be between 0 and 1
    :type min_prob: float
    :return: Resulting Stochastic Parity Game
    :rtype: StochasticParityGame
    """
    if not (0 < min_prob <= 1):
        print_error("min_prob must be between 0 and 1")
    vertices = {}
    for i in range(length + 1):
        if i == length:
            vertices["v" + str(i)] = SpgVertex(name="v" + str(i), is_eve=True, priority=0)
        else:
            vertices["v" + str(i)] = SpgVertex(name="v" + str(i), is_eve=True, priority=1)
    transitions = {}
    for i in range(length):
        transitions[(vertices["v" + str(i)], "next")] = SpgTransition(start_vertex=vertices["v" + str(i)], end_vertices={(min_prob, vertices["v" + str(i + 1)]), (1 - min_prob, vertices["v" + "0"])}, action="next")
    transitions[(vertices["v" + str(length)], "end")] = SpgTransition(start_vertex=vertices["v" + str(length)], end_vertices={(1.0, vertices["v" + str(length)])}, action="end")
    initial_vertex = vertices["v0"]
    return StochasticParityGame(vertices=vertices, transitions=transitions, init_vertex=initial_vertex)


def create_small_mutex_spg() -> StochasticParityGame:

    vertices = {
        "start":    SpgVertex(name="start",     is_eve=True,    priority=3),
        "(N,N,0)":  SpgVertex(name="(N,N,0)",   is_eve=True,    priority=3),
        "(N,N,1)":  SpgVertex(name="(N,N,1)",   is_eve=False,   priority=3),
        "(N,C,0)":  SpgVertex(name="(N,C,0)",   is_eve=True,    priority=2),
        "(N,C,1)":  SpgVertex(name="(N,C,1)",   is_eve=False,   priority=2),
        "(C,N,0)":  SpgVertex(name="(C,N,0)",   is_eve=True,    priority=2),
        "(C,N,1)":  SpgVertex(name="(C,N,1)",   is_eve=False,   priority=2),
        "(C,C,0)":  SpgVertex(name="(C,C,0)",   is_eve=True,    priority=1),
        "(C,C,1)":  SpgVertex(name="(C,C,1)",   is_eve=False,   priority=1)
    }
    transitions = {
        (vertices["start"], "start"):   SpgTransition(start_vertex=vertices["start"], end_vertices={(0.5, vertices["(N,N,0)"]), (0.5, vertices["(N,N,1)"])}, action="start"),
        (vertices["(N,N,0)"], "stay"):  SpgTransition(start_vertex=vertices["(N,N,0)"], end_vertices={(0.5, vertices["(N,N,0)"]), (0.5, vertices["(N,N,1)"])}, action="stay"),
        (vertices["(N,N,0)"], "enter"): SpgTransition(start_vertex=vertices["(N,N,0)"], end_vertices={(0.5, vertices["(C,N,0)"]), (0.5, vertices["(C,N,1)"])}, action="enter"),
        (vertices["(N,N,1)"], "stay"):  SpgTransition(start_vertex=vertices["(N,N,1)"], end_vertices={(0.5, vertices["(N,N,0)"]), (0.5, vertices["(N,N,1)"])}, action="stay"),
        (vertices["(N,N,1)"], "enter"): SpgTransition(start_vertex=vertices["(N,N,1)"], end_vertices={(0.5, vertices["(N,C,0)"]), (0.5, vertices["(N,C,1)"])}, action="enter"),
        (vertices["(N,C,0)"], "stay"):  SpgTransition(start_vertex=vertices["(N,C,0)"], end_vertices={(0.5, vertices["(N,C,0)"]), (0.5, vertices["(N,C,1)"])}, action="stay"),
        (vertices["(N,C,0)"], "enter"): SpgTransition(start_vertex=vertices["(N,C,0)"], end_vertices={(0.5, vertices["(C,C,0)"]), (0.5, vertices["(C,C,1)"])}, action="enter"),
        (vertices["(N,C,1)"], "exit"):  SpgTransition(start_vertex=vertices["(N,C,1)"], end_vertices={(0.5, vertices["(N,N,0)"]), (0.5, vertices["(N,N,1)"])}, action="exit"),
        (vertices["(C,N,0)"], "exit"):  SpgTransition(start_vertex=vertices["(C,N,0)"], end_vertices={(0.5, vertices["(N,N,0)"]), (0.5, vertices["(N,N,1)"])}, action="exit"),
        (vertices["(C,N,1)"], "stay"):  SpgTransition(start_vertex=vertices["(C,N,1)"], end_vertices={(0.5, vertices["(C,N,0)"]), (0.5, vertices["(C,N,1)"])}, action="stay"),
        (vertices["(C,N,1)"], "enter"): SpgTransition(start_vertex=vertices["(C,N,1)"], end_vertices={(0.5, vertices["(C,C,0)"]), (0.5, vertices["(C,C,1)"])}, action="enter"),
        (vertices["(C,C,0)"], "exit"):  SpgTransition(start_vertex=vertices["(C,C,0)"], end_vertices={(0.5, vertices["(N,C,0)"]), (0.5, vertices["(N,C,1)"])}, action="exit"),
        (vertices["(C,C,1)"], "exit"):  SpgTransition(start_vertex=vertices["(C,C,1)"], end_vertices={(0.5, vertices["(C,N,0)"]), (0.5, vertices["(C,N,1)"])}, action="exit")

    }
    initial_vertex = vertices["start"]
    return StochasticParityGame(vertices=vertices, transitions=transitions, init_vertex=initial_vertex)


def create_mutex_spg() -> StochasticParityGame:
    """
    Creates a Stochastic Parity Game that represents a mutex (mutual exclusion) problem.
    :return: Resulting Stochastic Parity Game
    :rtype: StochasticParityGame
    """
    vertices = {
        "start":    SpgVertex(name="start",     is_eve=True,    priority=3),
        "(N,N,0)":  SpgVertex(name="(N,N,0)",   is_eve=True,    priority=3),
        "(N,N,1)":  SpgVertex(name="(N,N,1)",   is_eve=False,   priority=3),
        "(N,T,0)":  SpgVertex(name="(N,T,0)",   is_eve=True,    priority=3),
        "(N,T,1)":  SpgVertex(name="(N,T,1)",   is_eve=False,   priority=3),
        "(N,C,0)":  SpgVertex(name="(N,C,0)",   is_eve=True,    priority=2),
        "(N,C,1)":  SpgVertex(name="(N,C,1)",   is_eve=False,   priority=2),
        "(T,N,0)":  SpgVertex(name="(T,N,0)",   is_eve=True,    priority=3),
        "(T,N,1)":  SpgVertex(name="(T,N,1)",   is_eve=False,   priority=3),
        "(T,T,0)":  SpgVertex(name="(T,T,0)",   is_eve=True,    priority=3),
        "(T,T,1)":  SpgVertex(name="(T,T,1)",   is_eve=False,   priority=3),
        "(T,C,0)":  SpgVertex(name="(T,C,0)",   is_eve=True,    priority=2),
        "(T,C,1)":  SpgVertex(name="(T,C,1)",   is_eve=False,   priority=2),
        "(C,N,0)":  SpgVertex(name="(C,N,0)",   is_eve=True,    priority=2),
        "(C,N,1)":  SpgVertex(name="(C,N,1)",   is_eve=False,   priority=2),
        "(C,T,0)":  SpgVertex(name="(C,T,0)",   is_eve=True,    priority=2),
        "(C,T,1)":  SpgVertex(name="(C,T,1)",   is_eve=False,   priority=2),
        "(C,C,0)":  SpgVertex(name="(C,C,0)",   is_eve=True,    priority=1),
        "(C,C,1)":  SpgVertex(name="(C,C,1)",   is_eve=False,   priority=1)
    }
    transitions = {
        (vertices["start"], "start"):   SpgTransition(start_vertex=vertices["start"], end_vertices={(0.5, vertices["(N,N,0)"]), (0.5, vertices["(N,N,1)"])}, action="start"),
        (vertices["(N,N,0)"], "stay"):  SpgTransition(start_vertex=vertices["(N,N,0)"], end_vertices={(0.5, vertices["(N,N,0)"]), (0.5, vertices["(N,N,1)"])}, action="stay"),
        (vertices["(N,N,0)"], "try"):   SpgTransition(start_vertex=vertices["(N,N,0)"], end_vertices={(0.5, vertices["(T,N,0)"]), (0.5, vertices["(T,N,1)"])}, action="try"),
        (vertices["(N,N,1)"], "stay"):  SpgTransition(start_vertex=vertices["(N,N,1)"], end_vertices={(0.5, vertices["(N,N,0)"]), (0.5, vertices["(N,N,1)"])}, action="stay"),
        (vertices["(N,N,1)"], "try"):   SpgTransition(start_vertex=vertices["(N,N,1)"], end_vertices={(0.5, vertices["(N,T,0)"]), (0.5, vertices["(N,T,1)"])}, action="try"),
        (vertices["(N,T,0)"], "stay"):  SpgTransition(start_vertex=vertices["(N,T,0)"], end_vertices={(0.5, vertices["(N,T,0)"]), (0.5, vertices["(N,T,1)"])}, action="stay"),
        (vertices["(N,T,0)"], "try"):   SpgTransition(start_vertex=vertices["(N,T,0)"], end_vertices={(0.5, vertices["(T,T,0)"]), (0.5, vertices["(T,T,1)"])}, action="try"),
        (vertices["(N,T,1)"], "enter"): SpgTransition(start_vertex=vertices["(N,T,1)"], end_vertices={(0.5, vertices["(N,C,0)"]), (0.5, vertices["(N,C,1)"])}, action="enter"),
        (vertices["(N,C,0)"], "stay"):  SpgTransition(start_vertex=vertices["(N,C,0)"], end_vertices={(0.5, vertices["(N,C,0)"]), (0.5, vertices["(N,C,1)"])}, action="stay"),
        (vertices["(N,C,0)"], "try"):   SpgTransition(start_vertex=vertices["(N,C,0)"], end_vertices={(0.5, vertices["(T,C,0)"]), (0.5, vertices["(T,C,1)"])}, action="try"),
        (vertices["(N,C,1)"], "exit"):  SpgTransition(start_vertex=vertices["(N,C,1)"], end_vertices={(0.5, vertices["(N,N,0)"]), (0.5, vertices["(N,N,1)"])}, action="exit"),
        (vertices["(T,N,0)"], "enter"): SpgTransition(start_vertex=vertices["(T,N,0)"], end_vertices={(0.5, vertices["(C,N,0)"]), (0.5, vertices["(C,N,1)"])}, action="enter"),
        (vertices["(T,N,1)"], "stay"):  SpgTransition(start_vertex=vertices["(T,N,1)"], end_vertices={(0.5, vertices["(T,N,0)"]), (0.5, vertices["(T,N,1)"])}, action="stay"),
        (vertices["(T,N,1)"], "try"):   SpgTransition(start_vertex=vertices["(T,N,1)"], end_vertices={(0.5, vertices["(T,T,0)"]), (0.5, vertices["(T,T,1)"])}, action="try"),
        (vertices["(T,T,0)"], "enter"): SpgTransition(start_vertex=vertices["(T,T,0)"], end_vertices={(0.5, vertices["(C,T,0)"]), (0.5, vertices["(C,T,1)"])}, action="enter"),
        (vertices["(T,T,1)"], "enter"): SpgTransition(start_vertex=vertices["(T,T,1)"], end_vertices={(0.5, vertices["(T,C,0)"]), (0.5, vertices["(T,C,1)"])}, action="enter"),
        (vertices["(T,C,0)"], "enter"): SpgTransition(start_vertex=vertices["(T,C,0)"], end_vertices={(0.5, vertices["(C,C,0)"]), (0.5, vertices["(C,C,1)"])}, action="enter"),
        (vertices["(T,C,1)"], "exit"):  SpgTransition(start_vertex=vertices["(T,C,1)"], end_vertices={(0.5, vertices["(T,N,0)"]), (0.5, vertices["(T,N,1)"])}, action="exit"),
        (vertices["(C,N,0)"], "exit"):  SpgTransition(start_vertex=vertices["(C,N,0)"], end_vertices={(0.5, vertices["(N,N,0)"]), (0.5, vertices["(N,N,1)"])}, action="exit"),
        (vertices["(C,N,1)"], "stay"):  SpgTransition(start_vertex=vertices["(C,N,1)"], end_vertices={(0.5, vertices["(C,N,0)"]), (0.5, vertices["(C,N,1)"])}, action="stay"),
        (vertices["(C,N,1)"], "try"):   SpgTransition(start_vertex=vertices["(C,N,1)"], end_vertices={(0.5, vertices["(C,T,0)"]), (0.5, vertices["(C,T,1)"])}, action="try"),
        (vertices["(C,T,0)"], "exit"):  SpgTransition(start_vertex=vertices["(C,T,0)"], end_vertices={(0.5, vertices["(N,T,0)"]), (0.5, vertices["(N,T,1)"])}, action="exit"),
        (vertices["(C,T,1)"], "enter"): SpgTransition(start_vertex=vertices["(C,T,1)"], end_vertices={(0.5, vertices["(C,C,0)"]), (0.5, vertices["(C,C,1)"])}, action="enter"),
        (vertices["(C,C,0)"], "exit"):  SpgTransition(start_vertex=vertices["(C,C,0)"], end_vertices={(0.5, vertices["(N,C,0)"]), (0.5, vertices["(N,C,1)"])}, action="exit"),
        (vertices["(C,C,1)"], "exit"):  SpgTransition(start_vertex=vertices["(C,C,1)"], end_vertices={(0.5, vertices["(C,N,0)"]), (0.5, vertices["(C,N,1)"])}, action="exit")
    }
    initial_vertex = vertices["start"]
    return StochasticParityGame(vertices=vertices, transitions=transitions, init_vertex=initial_vertex)


def create_frozen_lake_spg(columns: int, rows: int, point0: tuple[int, int] | None = None, point1: tuple[int, int] | None = None, share_of_holes: float = 0.5, wind_probability: float = 0.5, slide_probability: float = 0.5) -> StochasticParityGame:
    """
    Creates a Stochastic Parity Game that represents a frozen lake scenario.
    :param columns: Number of columns in the grid.
    :type columns: int
    :param rows: Number of rows in the grid.
    :type rows: int
    :param point0: Location of the first target point, if None, a random point will be chosen.
    :type point0: tuple[int, int] | None
    :param point1: Location of the second target point, if None, a random point will be chosen.
    :type point1: tuple[int, int] | None
    :param share_of_holes: Share of holes in the grid, must be between 0 and 1.
    :type share_of_holes: float
    :param wind_probability: Probability of wind having an action after a move, must be between 0 and 1.
    :type wind_probability: float
    :param slide_probability: Probability of sliding one field further after a move, must be between 0 and 1.
    :type slide_probability: float
    :return: Resulting Stochastic Parity Game
    :rtype: StochasticParityGame
    """
    field = [[2 for _ in range(rows)] for _ in range(columns)]
    if point0 is not None and point1 is not None:
        if point0 == point1:
            print_error(f"point1 and point2 must be different, but they are both {point0}.")
    if point0 is not None:
        if not (0 <= point0[0] < columns and 0 <= point0[1] < rows):
            print_error(f"point1 {point0} is out of bounds for a {columns}x{rows} grid.")
    if point1 is not None:
        if not (0 <= point1[0] < columns and 0 <= point1[1] < rows):
            print_error(f"point2 {point1} is out of bounds for a {columns}x{rows} grid.")
    if share_of_holes < 0 or share_of_holes > 1:
        print_error(f"share_of_holes must be between 0 and 1, but it is {share_of_holes}.")
    if point0 is None:
        point0 = (random.randint(0, columns - 1), random.randint(0, rows - 1))
        if point1 is not None:
            while point0 == point1:
                point0 = (random.randint(0, columns - 1), random.randint(0, rows - 1))
    if point1 is None:
        point1 = (random.randint(0, columns - 1), random.randint(0, rows - 1))
        if point0 == point1:
            while point1 == point0:
                point1 = (random.randint(0, columns - 1), random.randint(0, rows - 1))
    field[point0[0]][point0[1]] = 0
    field[point1[0]][point1[1]] = 1
    number_of_holes = int(columns * rows * share_of_holes)
    holes = set()
    while number_of_holes > 0:
        x = random.randint(0, columns - 1)
        y = random.randint(0, rows - 1)
        if field[x][y] == 2:
            field[x][y] = 3
            holes.add((x, y))
            number_of_holes -= 1
        else:
            while field[x][y] != 2:
                x = random.randint(0, columns - 1)
                y = random.randint(0, rows - 1)
            field[x][y] = 3
            holes.add((x, y))
            number_of_holes -= 1
    vertices = dict()
    for x in range(columns):
        for y in range(rows):
            if field[x][y] == 0:
                vertices[f"v_{x}_{y}_0_0"] = SpgVertex(name=f"v_{x}_{y}_0_0", is_eve=True, priority=2)
                vertices[f"v_{x}_{y}_0_1"] = SpgVertex(name=f"v_{x}_{y}_0_1", is_eve=True, priority=3)
                vertices[f"v_{x}_{y}_1_1"] = SpgVertex(name=f"v_{x}_{y}_1_1", is_eve=False, priority=3)
            elif field[x][y] == 1:
                vertices[f"v_{x}_{y}_0_0"] = SpgVertex(name=f"v_{x}_{y}_0_0", is_eve=True, priority=3)
                vertices[f"v_{x}_{y}_1_0"] = SpgVertex(name=f"v_{x}_{y}_1_0", is_eve=False, priority=3)
                vertices[f"v_{x}_{y}_0_1"] = SpgVertex(name=f"v_{x}_{y}_0_1", is_eve=True, priority=2)
            elif field[x][y] == 2:
                vertices[f"v_{x}_{y}_0_0"] = SpgVertex(name=f"v_{x}_{y}_0_0", is_eve=True, priority=3)
                vertices[f"v_{x}_{y}_1_0"] = SpgVertex(name=f"v_{x}_{y}_1_0", is_eve=False, priority=3)
                vertices[f"v_{x}_{y}_0_1"] = SpgVertex(name=f"v_{x}_{y}_0_1", is_eve=True, priority=3)
                vertices[f"v_{x}_{y}_1_1"] = SpgVertex(name=f"v_{x}_{y}_1_1", is_eve=False, priority=3)
            elif field[x][y] == 3:
                vertices[f"v_{x}_{y}_0_0"] = SpgVertex(name=f"v_{x}_{y}_0_0", is_eve=True, priority=1)
                vertices[f"v_{x}_{y}_0_1"] = SpgVertex(name=f"v_{x}_{y}_0_1", is_eve=True, priority=1)

    transitions = dict()
    for x in range(columns):
        for y in range(rows):
            match field[x][y]:
                case 0:
                    # change the current target to the other target field
                    transitions[(vertices[f"v_{x}_{y}_0_0"], "change_target")] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={(1.0, vertices[f"v_{x}_{y}_0_1"])}, action="change_target")
                    for direction in ["left", "right", "up", "down"]:
                        match direction:
                            case "left":
                                next_field = field[x - 1][y] if x > 0 else None
                                second_next_field = field[x - 2][y] if x > 1 else None
                                move = (-1, 0)
                            case "right":
                                next_field = field[x + 1][y] if x < columns - 1 else None
                                second_next_field = field[x + 2][y] if x < columns - 2 else None
                                move = (1, 0)
                            case "up":
                                next_field = field[x][y - 1] if y > 0 else None
                                second_next_field = field[x][y - 2] if y > 1 else None
                                move = (0, -1)
                            case "down":
                                next_field = field[x][y + 1] if y < rows - 1 else None
                                second_next_field = field[x][y + 2] if y < rows - 2 else None
                                move = (0, 1)
                        match (next_field, second_next_field):
                            case (None, _):
                                pass
                            case (1, _):
                                transitions[(vertices[f"v_{x}_{y}_0_1"], direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action=direction)
                                transitions[(vertices[f"v_{x}_{y}_1_1"], "blow_" + direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (2, None):
                                transitions[(vertices[f"v_{x}_{y}_0_1"], direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={(1-wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"]), (wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_1"])}, action=direction)
                                transitions[(vertices[f"v_{x}_{y}_1_1"], "blow_" + direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (2, 1):
                                transitions[(vertices[f"v_{x}_{y}_0_1"], direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"]), (slide_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_1"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_1"])}, action=direction)
                                transitions[(vertices[f"v_{x}_{y}_1_1"], "blow_" + direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (2, 2):
                                transitions[(vertices[f"v_{x}_{y}_0_1"], direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"]), (slide_probability * (1 - wind_probability), vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_1"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_1"]), (slide_probability * wind_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_1_1"])}, action=direction)
                                transitions[(vertices[f"v_{x}_{y}_1_1"], "blow_" + direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (2, 3):
                                transitions[(vertices[f"v_{x}_{y}_0_1"], direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"]), (slide_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_1"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_1"])}, action=direction)
                                transitions[(vertices[f"v_{x}_{y}_1_1"], "blow_" + direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (3, _):
                                transitions[(vertices[f"v_{x}_{y}_0_1"], direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action=direction)
                                transitions[(vertices[f"v_{x}_{y}_1_1"], "blow_" + direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)

                case 1:
                    # change the current target to the other target field
                    transitions[(vertices[f"v_{x}_{y}_0_1"], "change_target")] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={(1.0, vertices[f"v_{x}_{y}_0_0"])}, action="change_target")
                    for direction in ["left", "right", "up", "down"]:
                        match direction:
                            case "left":
                                next_field = field[x - 1][y] if x > 0 else None
                                second_next_field = field[x - 2][y] if x > 1 else None
                                move = (-1, 0)
                            case "right":
                                next_field = field[x + 1][y] if x < columns - 1 else None
                                second_next_field = field[x + 2][y] if x < columns - 2 else None
                                move = (1, 0)
                            case "up":
                                next_field = field[x][y - 1] if y > 0 else None
                                second_next_field = field[x][y - 2] if y > 1 else None
                                move = (0, -1)
                            case "down":
                                next_field = field[x][y + 1] if y < rows - 1 else None
                                second_next_field = field[x][y + 2] if y < rows - 2 else None
                                move = (0, 1)
                        match (next_field, second_next_field):
                            case (None, _):
                                pass
                            case (0, _):
                                transitions[(vertices[f"v_{x}_{y}_0_0"], direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action=direction)
                                transitions[(vertices[f"v_{x}_{y}_1_0"], "blow_" + direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                            case (2, None):
                                transitions[(vertices[f"v_{x}_{y}_0_0"], direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={(1-wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"]), (wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_0"])}, action=direction)
                                transitions[(vertices[f"v_{x}_{y}_1_0"], "blow_" + direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                            case (2, 0):
                                transitions[(vertices[f"v_{x}_{y}_0_0"], direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"]), (slide_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_0"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_0"])}, action=direction)
                                transitions[(vertices[f"v_{x}_{y}_1_0"], "blow_" + direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                            case (2, 2):
                                transitions[(vertices[f"v_{x}_{y}_0_0"], direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"]), (slide_probability * (1 - wind_probability), vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_0"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_0"]), (slide_probability * wind_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_1_0"])}, action=direction)
                                transitions[(vertices[f"v_{x}_{y}_1_0"], "blow_" + direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                            case (2, 3):
                                transitions[(vertices[f"v_{x}_{y}_0_0"], direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"]), (slide_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_0"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_0"])}, action=direction)
                                transitions[(vertices[f"v_{x}_{y}_1_0"], "blow_" + direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                            case (3, _):
                                transitions[(vertices[f"v_{x}_{y}_0_0"], direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action=direction)
                                transitions[(vertices[f"v_{x}_{y}_1_0"], "blow_" + direction)] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                case 2:
                    for direction in ["left", "right", "up", "down"]:
                        match direction:
                            case "left":
                                next_field = field[x - 1][y] if x > 0 else None
                                second_next_field = field[x - 2][y] if x > 1 else None
                                move = (-1, 0)
                            case "right":
                                next_field = field[x + 1][y] if x < columns - 1 else None
                                second_next_field = field[x + 2][y] if x < columns - 2 else None
                                move = (1, 0)
                            case "up":
                                next_field = field[x][y - 1] if y > 0 else None
                                second_next_field = field[x][y - 2] if y > 1 else None
                                move = (0, -1)
                            case "down":
                                next_field = field[x][y + 1] if y < rows - 1 else None
                                second_next_field = field[x][y + 2] if y < rows - 2 else None
                                move = (0, 1)
                        match (next_field, second_next_field):
                            case (None, _):
                                pass
                            case (0, None):
                                transitions[vertices[f"v_{x}_{y}_0_0"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_0_1"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={(1 - wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"]), (wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_1"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_1_0"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                                transitions[vertices[f"v_{x}_{y}_1_1"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (0, 1):
                                transitions[vertices[f"v_{x}_{y}_0_0"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_0_1"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"]), (slide_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_1"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_1"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_1_0"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                                transitions[vertices[f"v_{x}_{y}_1_1"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (0, 2):
                                transitions[vertices[f"v_{x}_{y}_0_0"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_0_1"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"]), (slide_probability * (1 - wind_probability), vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_1"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_1"]), (slide_probability * wind_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_1_1"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_1_0"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                                transitions[vertices[f"v_{x}_{y}_1_1"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (0, 3):
                                transitions[vertices[f"v_{x}_{y}_0_0"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_0_1"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"]), (slide_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_1"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_1"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_1_0"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                                transitions[vertices[f"v_{x}_{y}_1_1"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (1, None):
                                transitions[vertices[f"v_{x}_{y}_0_1"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_0_0"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={(1 - wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"]), (wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_0"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_1_0"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                                transitions[vertices[f"v_{x}_{y}_1_1"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (1, 0):
                                transitions[vertices[f"v_{x}_{y}_0_1"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_0_0"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"]), (slide_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_0"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_0"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_1_0"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                                transitions[vertices[f"v_{x}_{y}_1_1"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (1, 2):
                                transitions[vertices[f"v_{x}_{y}_0_1"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_0_0"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"]), (slide_probability * (1 - wind_probability), vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_0"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_0"]), (slide_probability * wind_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_1_0"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_1_0"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                                transitions[vertices[f"v_{x}_{y}_1_1"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (1, 3):
                                transitions[vertices[f"v_{x}_{y}_0_1"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_0_0"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"]), (slide_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_0"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_0"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_1_0"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                                transitions[vertices[f"v_{x}_{y}_1_1"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (2, None):
                                transitions[vertices[f"v_{x}_{y}_0_0"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={(1 - wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"]), (wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_0"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_0_1"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={(1 - wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"]), (wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_1"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_1_0"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                                transitions[vertices[f"v_{x}_{y}_1_1"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (2, 0):
                                transitions[vertices[f"v_{x}_{y}_0_0"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"]), (slide_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_0"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_0"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_0_1"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"]), (slide_probability * (1 - wind_probability), vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_1"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_1"]), (slide_probability * wind_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_1_1"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_1_0"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                                transitions[vertices[f"v_{x}_{y}_1_1"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (2, 1):
                                transitions[vertices[f"v_{x}_{y}_0_0"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"]), (slide_probability * (1 - wind_probability), vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_0"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_0"]), (slide_probability * wind_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_1_0"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_0_1"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"]), (slide_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_1"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_1"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_1_0"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                                transitions[vertices[f"v_{x}_{y}_1_1"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (2, 2):
                                transitions[vertices[f"v_{x}_{y}_0_0"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"]), (slide_probability * (1 - wind_probability), vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_0"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_0"]), (slide_probability * wind_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_1_0"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_0_1"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"]), (slide_probability * (1 - wind_probability), vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_1"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_1"]), (slide_probability * wind_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_1_1"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_1_0"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                                transitions[vertices[f"v_{x}_{y}_1_1"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (2, 3):
                                transitions[vertices[f"v_{x}_{y}_0_0"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"]), (slide_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_0"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_0"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_0_1"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={((1 - slide_probability) * (1 - wind_probability), vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"]), (slide_probability, vertices[f"v_{x + 2 * move[0]}_{y + 2 * move[1]}_0_1"]), ((1 - slide_probability) * wind_probability, vertices[f"v_{x + move[0]}_{y + move[1]}_1_1"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_1_0"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                                transitions[vertices[f"v_{x}_{y}_1_1"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                            case (3, _):
                                transitions[vertices[f"v_{x}_{y}_0_0"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_0_1"], direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action=direction)
                                transitions[vertices[f"v_{x}_{y}_1_0"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_0"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_0"])}, action="blow_" + direction)
                                transitions[vertices[f"v_{x}_{y}_1_1"], "blow_" + direction] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_1_1"], end_vertices={(1.0, vertices[f"v_{x + move[0]}_{y + move[1]}_0_1"])}, action="blow_" + direction)
                case 3:
                    # if fallen into a hole, go back to the current start field
                    transitions[(vertices[f"v_{x}_{y}_0_0"], "go_back")] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_0"], end_vertices={(1.0, vertices[f"v_{point1[0]}_{point1[1]}_0_0"])}, action="go_back")
                    transitions[(vertices[f"v_{x}_{y}_0_1"], "go_back")] = SpgTransition(start_vertex=vertices[f"v_{x}_{y}_0_1"], end_vertices={(1.0, vertices[f"v_{point0[0]}_{point0[1]}_0_0"])}, action="go_back")
    initial_vertex = vertices[f"v_{point0[0]}_{point0[1]}_0_0"]
    return StochasticParityGame(vertices=vertices, transitions=transitions, init_vertex=initial_vertex)


def create_random_spg(number_of_vertices: int, number_of_outgoing_transitions: int, number_of_priorities: int) -> StochasticParityGame:
    """
    Creates a random stochastic parity game with the specified number of vertices, outgoing transitions, and priorities.
    :param number_of_vertices: Number of vertices in the game
    :type number_of_vertices: int
    :param number_of_outgoing_transitions: Number of outgoing transitions for each vertex
    :type number_of_outgoing_transitions: int
    :param number_of_priorities: Number of priorities in the game
    :type number_of_priorities: int
    :return: Resulting random stochastic parity game
    :rtype: StochasticParityGame
    """
    vertices = {f"v_{i}": SpgVertex(name=f"v_{i}", is_eve=True if random.randint(0, 1) == 1 else False, priority=random.randint(0, number_of_priorities - 1)) for i in range(number_of_vertices)}
    transitions = {}
    for vertex in vertices.values():
        for i in range(number_of_outgoing_transitions):
            if i == 0:
                random_vertex1 = random.choice(list(vertices.values()))
                random_vertex2 = random.choice(list(vertices.values()))
                while random_vertex2 == random_vertex1:
                    random_vertex2 = random.choice(list(vertices.values()))
                transitions[(vertex, f"action_{i}")] = SpgTransition(start_vertex=vertex, end_vertices={(0.5, random_vertex1), (0.5, random_vertex2)}, action=f"action_{i}")
            else:
                if random.randint(0, 1) == 1:
                    transitions[(vertex, f"action_{i}")] = SpgTransition(start_vertex=vertex, end_vertices={(1.0, random.choice(list(vertices.values())))}, action=f"action_{i}")
                else:
                    random_vertex1 = random.choice(list(vertices.values()))
                    random_vertex2 = random.choice(list(vertices.values()))
                    while random_vertex2 == random_vertex1:
                        random_vertex2 = random.choice(list(vertices.values()))
                    transitions[(vertex, f"action_{i}")] = SpgTransition(start_vertex=vertex, end_vertices={(0.5, random_vertex1), (0.5, random_vertex2)}, action=f"action_{i}")
    initial_vertex = random.choice(list(vertices.values()))
    return StochasticParityGame(vertices, transitions, initial_vertex)


def benchmark_own_examples_for_correctness(filenames_of_benchmarks: list[str], expected_values: list[tuple[float, float]], use_global_path=False, debug: bool = False) -> None:
    """
    Benchmarks own examples for correctness by comparing the expected values with the computed results.
    :param filenames_of_benchmarks: List of filenames of benchmark files
    :type filenames_of_benchmarks: list[str]
    :param expected_values: List of tuples containing expected minimum and maximum probabilities
    :type expected_values: list[tuple[float, float]]
    :param use_global_path: Whether to use the global path for file operations
    :type use_global_path: bool
    :param debug: Whether to print debug information
    :type debug: bool
    """
    if len(filenames_of_benchmarks) != len(expected_values):
        raise ValueError("The number of benchmark files must match the number of expected values.")
    i = 0
    for filename in filenames_of_benchmarks:
        spg = read_spg_from_file(filename, use_global_path=use_global_path)
        ssg = spg_to_ssg(spg=spg, epsilon=1e-6, print_alphas=True)
        smg_spec = ssg_to_smgspec(ssg=ssg, version1=True, debug=False, print_correspondingvertices=True)
        save_smg_file(smg_spec, file_name="temp.smg", use_global_path=use_global_path, force=True)
        result = check_target_reachability(smg_file="temp.smg", print_probabilities=False, use_global_path=use_global_path)
        print("####################################################################################")
        print()
        print(f"Expected minimum probability of Eve winning with even parity for {filename}: {expected_values[i][0]}")
        print(f"Computed minimum probability of Eve winning with even parity for {filename}: {result[0]}")
        print("---------------------------------------------------------------------------------------")
        print(f"Expected maximum probability of Eve winning with even parity for {filename}: {expected_values[i][1]}")
        print(f"Computed maximum probability of Eve winning with even parity for {filename}: {result[1]}")
        print()
        i += 1


def benchmark_chain_spgs_for_correctness(use_global_path: bool = False, debug: bool = GLOBAL_DEBUG) -> None:
    """
    Benchmarks chain SPGs for correctness by checking the reachability of the target.
    :param use_global_path: Whether to use the global path for file operations
    :type use_global_path: bool
    :param debug: Whether to print debug information
    :type debug: bool
    """
    for i in range(1, 20):
        spg = create_chain_spg(length=2 ** i, min_prob=0.5)
        ssg = spg_to_ssg(spg=spg, epsilon=1e-6, print_alphas=debug)
        smg_spec = ssg_to_smgspec(ssg=ssg, version1=True, debug=False, print_correspondingvertices=False)
        save_smg_file(smg_spec, file_name="temp.smg", use_global_path=use_global_path, force=True)
        result = check_target_reachability(smg_file="temp.smg", print_probabilities=False, use_global_path=use_global_path)
        print("####################################################################################")
        print()
        print(f"Expected minimum probability of Eve winning with even parity for chain of length {2 ** i}: 1.0")
        print(f"Computed minimum probability of Eve winning with even parity for chain of length {2 ** i}: {result[0]}")
        print("---------------------------------------------------------------------------------------")
        print(f"Expected maximum probability of Eve winning with even parity for chain of length {2 ** i}: 1.0")
        print(f"Computed maximum probability of Eve winning with even parity for chain of length {2 ** i}: {result[1]}")
        print()


def benchmark_mutex_spg_for_correctness(use_global_path: bool = False, debug: bool = GLOBAL_DEBUG) -> None:
    """
    Benchmarks mutex SPG for correctness by checking the reachability of the target.
    :param use_global_path: Whether to use the global path for file operations
    :type use_global_path: bool
    :param debug: Whether to print debug information
    :type debug: bool
    """
    spg = create_small_mutex_spg()
    ssg = spg_to_ssg(spg=spg, epsilon=1e-6, print_alphas=debug)
    smg_spec = ssg_to_smgspec(ssg=ssg, version1=True, debug=False, print_correspondingvertices=True)
    save_smg_file(smg_spec, file_name="temp.smg", use_global_path=use_global_path, force=True)
    from src.ssg_to_smg import create_dot_file, create_svg_file
    create_dot_file(smg_file="temp.smg", dot_file="temp.dot", use_global_path=use_global_path, force=True)
    create_svg_file(dot_file="temp.dot", svg_file="temp.svg", use_global_path=use_global_path, force=True, open_svg=True)
    result = check_target_reachability(smg_file="temp.smg", print_probabilities=False, use_global_path=use_global_path)
    print("####################################################################################")
    print()
    print(f"Expected probability of satisfied mutex condition when Eve tries to violate it: 0.0")
    print(f"Computed probability of satisfied mutex condition when Eve tries to violate it: {result[0]}")
    print("---------------------------------------------------------------------------------------")
    print(f"Expected probability of satisfied mutex condition when Eve tries to satisfy it: 0.0")
    print(f"Computed probability of satisfied mutex condition when Eve tries to satisfy it: {result[1]}")
    print()


def _iteration_worker(q, method_with_args, debug: bool = GLOBAL_DEBUG):
    """
    Worker function for running a method with arguments in a separate process.
    :param q: Queue for communication between processes
    :type q: multiprocessing.Queue
    :param method_with_args: Method and its arguments to be executed
    :type method_with_args: tuple[callable, tuple]
    """
    if debug:
        import traceback
        print("[Worker] Starte Subprozess...")
    method, args = method_with_args
    try:
        if debug:
            print(f"[Worker] Methode: {method.__name__}, args: {args}")
        result = method(*args)
        if debug:
            print("[Worker] Ergebnis erfolgreich erhalten.")
        q.put(result)
    except Exception as e:
        if debug:
            print("[Worker] Ausnahme aufgetreten:", e)
            traceback.print_exc()
        q.put(e)


def benchmark_frozen_lake(timeout: int = 3600, abort_when_alpha_underflow: bool = True, use_global_path: bool = False, debug: bool = True) -> dict:
    """
    Benchmarks the creation and transformation of a frozen lake SMG and the solving of a target reachability property.
    :param timeout: Number of seconds to wait for each subprocess before terminating it
    :type timeout: int
    :param abort_when_alpha_underflow: Whether to abort the benchmark when an alpha underflow is detected
    :type abort_when_alpha_underflow: bool
    :param use_global_path: Whether to use the global path for file operations
    :type use_global_path: bool
    :param debug: Whether to print debug information
    :type debug: bool
    :return: Dictionary containing benchmark results
    :rtype: dict
    """
    benchmark_results = dict()
    with Manager() as manager:
        for size in range(5, 11):
            q = manager.Queue()

            p = Process(target=_iteration_worker, args=(q, (create_frozen_lake_spg, (size, size, None, None, 0.1, 0.5, 0.5)), debug))
            start_time = time.perf_counter()
            if debug:
                print_debug(f"Start creating frozen lake benchmark for size {size} by {size}...")
            p.start()
            p.join(timeout)
            end_time = time.perf_counter()

            if p.is_alive():
                if debug:
                    print_debug(f"Timeout of {timeout} seconds reached for frozen lake creation with size {size} by {size}.")
                kill_process_and_children(p.pid)
                p.join()
            try:
                result = q.get(timeout=5)
                print(f"Creating frozen lake with size {size} by {size} took {end_time - start_time:.2f} seconds.")
                benchmark_results[(size, "spg_creation_time")] = end_time - start_time
                print(f"Size of SPG: {asizeof.asizeof(result)} bytes.")
                benchmark_results[(size, "spg_size")] = asizeof.asizeof(result)
            except pyqueue.Empty:
                print_error(f"Error: No result received from subprocess for creating frozen lake with size {size} by {size}.")
                break

            if isinstance(result, Exception):
                print_error(f"Subprocess failed with exception: {result}")
                break

            spg = result

            q = manager.Queue()
            p = Process(target=_iteration_worker, args=(q, (spg_to_ssg, (spg, 1e-6, True)), debug))
            start_time = time.perf_counter()
            if debug:
                print_debug(f"Start transforming frozen lake benchmark for size {size} by {size} to SSG...")
            p.start()
            p.join(timeout)
            end_time = time.perf_counter()

            if p.is_alive():
                if debug:
                    print_debug(f"Timeout of {timeout} seconds reached for transforming frozen lake with size {size} by {size}.")
                kill_process_and_children(p.pid)
                p.join()
            try:
                result = q.get(timeout=5)
                print(f"Transforming frozen lake with size {size} by {size} to SSG took {end_time - start_time:.2f} seconds.")
                benchmark_results[(size, "ssg_transformation_time")] = end_time - start_time
                print(f"Size of SSG: {asizeof.asizeof(result)} bytes.")
                benchmark_results[(size, "ssg_size")] = asizeof.asizeof(result)
            except pyqueue.Empty:
                print_error(f"Error: No result received from subprocess for transforming frozen lake with size {size} by {size}.")
                break

            if isinstance(result, Exception):
                print_error(f"Subprocess failed with exception: {result}")
                break

            ssg = result
            if ssg.has_alpha_underflow():
                print_warning(f"Alpha underflow detected in frozen lake with size {size} by {size}.")
                if abort_when_alpha_underflow:
                    break

            q = manager.Queue()
            p = Process(target=_iteration_worker, args=(q, (ssg_to_smgspec, (ssg, True, True, False)), debug))
            start_time = time.perf_counter()
            if debug:
                print_debug(f"Start transforming frozen lake benchmark for size {size} by {size} to SMG...")
            p.start()
            p.join(timeout)
            end_time = time.perf_counter()

            if p.is_alive():
                if debug:
                    print_debug(f"Timeout of {timeout} seconds reached for transforming frozen lake with size {size} by {size}.")
                kill_process_and_children(p.pid)
                p.join()
            try:
                result = q.get(timeout=5)
                print(f"Transforming frozen lake with size {size} by {size} to SMG took {end_time - start_time:.2f} seconds.")
                benchmark_results[(size, "smg_transformation_time")] = end_time - start_time
                print(f"Size of SMG specification: {asizeof.asizeof(result)} bytes.")
                benchmark_results[(size, "smg_size")] = asizeof.asizeof(result)
            except pyqueue.Empty:
                print_error(f"Error: No result received from subprocess for transforming frozen lake with size {size} by {size}.")
                break

            if isinstance(result, Exception):
                print_error(f"Subprocess failed with exception: {result}")
                break

            smgspec = result
            save_smg_file(content=smgspec, file_name=f"temp.smg", use_global_path=use_global_path, force=True)

            q = manager.Queue()
            p = Process(target=_iteration_worker, args=(q, (check_property, ("temp.smg", "<<eve>> Pmin=? [F \"target\"]", use_global_path, None, False)), debug))
            start_time = time.perf_counter()
            if debug:
                print_debug(f"Start checking first target reachability property of frozen lake benchmark for size {size} by {size}...")
            p.start()
            p.join(timeout)
            end_time = time.perf_counter()

            if p.is_alive():
                if debug:
                    print_debug(f"Timeout of {timeout} seconds reached for checking frozen lake with size {size} by {size}.")
                kill_process_and_children(p.pid)
                p.join()
            try:
                result = q.get(timeout=5)
                print(f"Checking frozen lake with size {size} by {size} to SMG took {end_time - start_time:.2f} seconds.")
                benchmark_results[(size, "property_check_time")] = end_time - start_time
            except pyqueue.Empty:
                print_error(f"Error: No result received from subprocess for transforming frozen lake with size {size} by {size}.")
                break

            if isinstance(result, Exception):
                print_error(f"Subprocess failed with exception: {result}")
                break

            result1 = result
            print(f"Probability of Eve winning when trying to lose: {result1}")

            q = manager.Queue()
            p = Process(target=_iteration_worker, args=(q, (check_property, ("temp.smg", "<<eve>> Pmax=? [F \"target\"]", use_global_path, None, False)), debug))
            start_time = time.perf_counter()
            if debug:
                print_debug(f"Start checking second target reachability property of frozen lake benchmark for size {size} by {size}...")
            p.start()
            p.join(timeout)
            end_time = time.perf_counter()

            if p.is_alive():
                if debug:
                    print_debug(f"Timeout of {timeout} seconds reached for checking frozen lake with size {size} by {size}.")
                kill_process_and_children(p.pid)
                p.join()
            try:
                result = q.get(timeout=5)
                print(f"Checking frozen lake with size {size} by {size} to SMG took {end_time - start_time:.2f} seconds.")
                benchmark_results[(size, "property_check_time_2")] = end_time - start_time
            except pyqueue.Empty:
                print_error(f"Error: No result received from subprocess for transforming frozen lake with size {size} by {size}.")
                break

            if isinstance(result, Exception):
                print_error(f"Subprocess failed with exception: {result}")
                break

            result2 = result
            print(f"Probability of Eve winning when trying to win: {result2}")
    return benchmark_results


def dict_from_tuples(data):
    nested = {}
    for key, value in data.items():
        current = nested
        for part in key[:-1]:
            current = current.setdefault(str(part), {})
        current[str(key[-1])] = value
    return nested


def nested_to_tuples(data, prefix=()):
    results = {}
    for k, v in data.items():
        if isinstance(v, dict):
            results.update(nested_to_tuples(v, prefix + (k,)))
        else:
            results[prefix + (k,)] = v
    return results


def kill_process_and_children(pid):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except psutil.NoSuchProcess:
        pass


def benchmark_random_spgs(number_of_vertices: list[int], share_of_outgoing_transitions: list[float], number_of_priorities: list[int], spg_transformation_epsilon: list[float], prism_algorithm: list[str], timeout: int = 3600, abort_when_alpha_underflow=True, use_global_path=False, save_results: bool = True, debug=True) -> dict:
    """
    Benchmarks the creation and transformation of random SPGs and the solving of target reachability properties.
    :param number_of_vertices: List of numbers of vertices for the random SPGs
    :type number_of_vertices: list[int]
    :param share_of_outgoing_transitions: List of shares of outgoing transitions for the random SPGs
    :type share_of_outgoing_transitions: list[float]
    :param number_of_priorities: List of numbers of priorities for the random SPGs
    :type number_of_priorities: list[int]
    :param spg_transformation_epsilon: List of epsilon values for the SPG transformation
    :type spg_transformation_epsilon: list[float]
    :param prism_algorithm: List of Prism algorithms to use for the transformation
    :type prism_algorithm: list[str]
    :param timeout: Number of seconds to wait for each subprocess before terminating it
    :type timeout: int
    :param abort_when_alpha_underflow: Whether to abort the benchmark when an alpha underflow is detected
    :type abort_when_alpha_underflow: bool
    :param use_global_path: Whether to use the global path for file operations
    :type use_global_path: bool
    :param save_results: Whether to save the benchmark results to a file
    :type save_results: bool
    :param debug: Whether to print debug information
    :type debug: bool
    :return: Dictionary containing benchmark results
    :rtype: dict
    """
    print(f"###Benchmarking {len(number_of_vertices) * len(share_of_outgoing_transitions) * len(number_of_priorities) * len(spg_transformation_epsilon) * len(prism_algorithm)} random SPGs" + (" that are saved to random_ssg_results.json" if save_results else " without saving results") + "###")
    benchmark_results = dict()
    if save_results:
        result_path = "random_ssg_results.json" if not use_global_path else os.path.join(GLOBAL_IN_OUT_PATH, "random_ssg_results.json")
        if os.path.exists(result_path):
            with open(result_path, "r") as f:
                benchmark_results = json.load(f)
                benchmark_results = nested_to_tuples(benchmark_results)
    with Manager() as manager:
        for n_of_vertices in number_of_vertices:
            for s_of_transitions in share_of_outgoing_transitions:
                for n_of_priorities in number_of_priorities:
                    for epsilon in spg_transformation_epsilon:
                        for algorithm in prism_algorithm:

                            print(f"#####Vertices : {n_of_vertices} || Share of transitions: {s_of_transitions} || Priorities: {n_of_priorities} || Epsilon: {epsilon} || Algorithm: {algorithm}")
                            q = manager.Queue()

                            p = Process(target=_iteration_worker,
                                        args=(q, (create_random_spg, (n_of_vertices, max(1, int(s_of_transitions * n_of_vertices)), n_of_priorities)), debug))
                            start_time = time.perf_counter()
                            if debug:
                                print_debug(f"Start creating random SPG for {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities...")
                            p.start()
                            p.join(timeout)
                            end_time = time.perf_counter()

                            if p.is_alive():
                                if debug:
                                    print_debug(f"Timeout of {timeout} seconds reached for creating random SPG for {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities.")
                                kill_process_and_children(p.pid)
                                p.join()
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "spg_creation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "spg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_1")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_2")] = -1.0
                                continue
                            try:
                                result = q.get(timeout=5)
                                print(f"Creating random SPG for {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities took {end_time - start_time:.2f} seconds.")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "spg_creation_time")] = end_time - start_time
                                print(f"Size of SPG: {asizeof.asizeof(result)} bytes.")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "spg_size")] = asizeof.asizeof(result)
                            except pyqueue.Empty:
                                print(
                                    f"No result received from subprocess for creating random SPG for {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities.")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "spg_creation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "spg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_1")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_2")] = -1.0
                                continue

                            if isinstance(result, Exception):
                                print(f"Subprocess failed with exception: {result}")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "spg_creation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "spg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_1")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_2")] = -1.0
                                continue

                            spg = result

                            q = manager.Queue()
                            p = Process(target=_iteration_worker, args=(q, (spg_to_ssg, (spg, epsilon, True)), debug))
                            start_time = time.perf_counter()
                            if debug:
                                print_debug(f"Start transforming random spg for {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities to SSG...")
                            p.start()
                            p.join(timeout)
                            end_time = time.perf_counter()

                            if p.is_alive():
                                if debug:
                                    print_debug(
                                        f"Timeout of {timeout} seconds reached for transforming random spg with {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities to SSG.")
                                kill_process_and_children(p.pid)
                                p.join()
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_1")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_2")] = -1.0
                                continue
                            try:
                                result = q.get(timeout=5)
                                print(f"Transforming random spg for {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities to SSG took {end_time - start_time:.2f} seconds.")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_transformation_time")] = end_time - start_time
                                print(f"Size of SSG: {asizeof.asizeof(result)} bytes.")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_size")] = asizeof.asizeof(result)
                            except pyqueue.Empty:
                                print(
                                    f"Error: No result received from subprocess for transforming random SPG for {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities to SSG.")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_1")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_2")] = -1.0
                                continue

                            if isinstance(result, Exception):
                                print(f"Subprocess failed with exception: {result}")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_1")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_2")] = -1.0
                                continue

                            ssg = result
                            if ssg.has_alpha_underflow():
                                print_warning(f"Alpha underflow detected in random SPG with {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities.")
                                if abort_when_alpha_underflow:
                                    benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_transformation_time")] = -1.0
                                    benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "ssg_size")] = -1
                                    benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_transformation_time")] = -1.0
                                    benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_size")] = -1
                                    benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_1")] = -1.0
                                    benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_2")] = -1.0
                                    continue

                            q = manager.Queue()
                            p = Process(target=_iteration_worker, args=(q, (ssg_to_smgspec, (ssg, True, True, False)), debug))
                            start_time = time.perf_counter()
                            if debug:
                                print_debug(f"Start transforming random spg for {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities to SMG...")
                            p.start()
                            p.join(timeout)
                            end_time = time.perf_counter()

                            if p.is_alive():
                                if debug:
                                    print_debug(
                                        f"Timeout of {timeout} seconds reached for transforming random spg with {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities to SMG.")
                                kill_process_and_children(p.pid)
                                p.join()
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_1")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_2")] = -1.0
                                continue
                            try:
                                result = q.get(timeout=5)
                                print(f"Transforming random spg for {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities to SMG took {end_time - start_time:.2f} seconds.")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_transformation_time")] = end_time - start_time
                                print(f"Size of SMG specification: {asizeof.asizeof(result)} bytes.")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_size")] = asizeof.asizeof(result)
                            except pyqueue.Empty:
                                print(
                                    f"Error: No result received from subprocess for transforming random spg for {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities to SMG.")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_1")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_2")] = -1.0
                                continue

                            if isinstance(result, Exception):
                                print(f"Subprocess failed with exception: {result}")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_transformation_time")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "smg_size")] = -1
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_1")] = -1.0
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_2")] = -1.0
                                continue

                            smgspec = result
                            save_smg_file(content=smgspec, file_name=f"temp.smg", use_global_path=use_global_path, force=True)

                            q = manager.Queue()
                            p = Process(target=_iteration_worker, args=(q, (check_property, ("temp.smg", "<<eve>> Pmin=? [F \"target\"]", use_global_path, None, False, PRISM_PATH, MAX_ITERS, PRISM_EPSILON, algorithm)), debug))
                            start_time = time.perf_counter()
                            if debug:
                                print_debug(f"Start checking first target reachability property for random spg for {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities...")
                            p.start()
                            p.join(timeout)
                            end_time = time.perf_counter()
                            check_worked = True
                            if p.is_alive():
                                if debug:
                                    print_debug(
                                        f"Timeout of {timeout} seconds reached for checking first target reachability property for random spg with {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities.")
                                kill_process_and_children(p.pid)
                                p.join()
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_1")] = -1.0
                                check_worked = False
                            if check_worked:
                                try:
                                    result = q.get(timeout=5)
                                    print(
                                        f"Checking first target reachability property for random spg with {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities took {end_time - start_time:.2f} seconds.")
                                    benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_1")] = end_time - start_time
                                except pyqueue.Empty:
                                    print(
                                        f"Error: No result received from subprocess for checking random spg with {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities.")
                                    check_worked = False
                                    benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_1")] = -1.0
                                if check_worked:
                                    if isinstance(result, Exception):
                                        print(f"Subprocess failed with exception: {result}")
                                        benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_1")] = -1.0

                            q = manager.Queue()
                            p = Process(target=_iteration_worker, args=(q, (check_property, ("temp.smg", "<<eve>> Pmax=? [F \"target\"]", use_global_path, None, False, PRISM_PATH, MAX_ITERS, PRISM_EPSILON, algorithm)), debug))

                            start_time = time.perf_counter()
                            if debug:
                                print_debug(
                                    f"Start checking second target reachability property for random spg for {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities...")
                            p.start()
                            p.join(timeout)
                            end_time = time.perf_counter()

                            if p.is_alive():
                                if debug:
                                    print_debug(
                                        f"Timeout of {timeout} seconds reached for checking first target reachability property for random spg with {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities.")
                                kill_process_and_children(p.pid)
                                p.join()
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_2")] = -1.0
                                continue
                            try:
                                result = q.get(timeout=5)
                                print(
                                    f"Checking second target reachability property for random spg with {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities took {end_time - start_time:.2f} seconds.")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_2")] = end_time - start_time
                            except pyqueue.Empty:
                                print(
                                    f"Error: No result received from subprocess for checking random spg with {n_of_vertices} vertices, {max(1, int(s_of_transitions * n_of_vertices))} outgoing transitions and {n_of_priorities} priorities.")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_2")] = -1.0
                                continue

                            if isinstance(result, Exception):
                                print(f"Subprocess failed with exception: {result}")
                                benchmark_results[(str(n_of_vertices), str(s_of_transitions), str(n_of_priorities), str(epsilon), str(algorithm), "property_check_time_2")] = -1.0
                                continue

                            if save_results:
                                with open(result_path, "w") as f:
                                    nested = dict_from_tuples(benchmark_results)
                                    json.dump(nested, f, indent=4)
    if save_results:
        with open(result_path, "w") as f:
            nested = dict_from_tuples(benchmark_results)
            json.dump(nested, f, indent=4)
    return benchmark_results


def main():
    """# benchmark_frozen_lake(3600, False, use_global_path=True, debug=True)"""
    number_of_vertices = [2, 3, 8, 15, 32, 63, 128, 255, 512, 1023]
    share_of_outgoing_transitions = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0]
    number_of_priorities = [2, 8, 32]
    spg_transformation_epsilon = [None, 1e-100, 1e-20, 1e-10, 1e-6, 1e-1]
    prism_algorithm = ["-valiter", "-politer"]
    res = benchmark_random_spgs(number_of_vertices, share_of_outgoing_transitions, number_of_priorities, spg_transformation_epsilon, prism_algorithm, timeout=600, abort_when_alpha_underflow=False, use_global_path=True, debug=True, save_results=True)

    print()
    """spg = create_frozen_lake_spg(columns=2, rows=2, point0=(0, 0), point1=(0, 1), share_of_holes=0)
    # spg = create_chain_spg(length=10, min_prob=0.5)
    ssg = spg_to_ssg(spg=spg, epsilon=1e-6, print_alphas=True)
    smg_spec = ssg_to_smgspec(ssg=ssg, version1=True, debug=False, print_correspondingvertices=True)
    save_smg_file(content=smg_spec, file_name="temp.smg", use_global_path=True, force=True)
    from ssg_to_smg import create_dot_file, create_svg_file
    check_target_reachability("temp.smg", print_probabilities=True, export_strategies=False, use_global_path=True, prism_solving_algorithm="-politer")
    create_dot_file("temp.smg", "temp.dot", use_global_path=True, force=True)
    create_svg_file("temp.dot", "temp.svg", use_global_path=True, force=True, open_svg=True)"""
    """benchmark_own_examples_for_correctness(["own_example1.spg"], [(0.0, 1/3)], use_global_path=True, debug=False)"""
    print()


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
