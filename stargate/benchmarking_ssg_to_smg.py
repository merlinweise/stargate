import random
import os
import matplotlib
import time
import contextlib
import io
import queue as pyqueue
import math

from multiprocessing import Process, Queue

from benchmarking_global import kill_process_and_children
from ssg_to_smg import ssg_to_smgspec, save_smg_file, check_target_reachability, check_smg_stats
from simplestochasticgame import SsgVertex, SsgTransition, SimpleStochasticGame, is_deadlock_vertex
from error_handling import print_error, print_debug, print_warning
from settings import GLOBAL_DEBUG,  GLOBAL_IN_OUT_PATH


def make_float_list_from_string(s: str) -> list[float]:
    """
    Converts a string representation of a list of integers into an actual list of integers.
    :param s: String representation of a list of integers
    :type s: str
    :return: List of integers
    :rtype: list[float]
    """
    try:
        new_list = []
        for x in s.strip("[]").split(","):
            new_list.append(float(x.strip()))
        return new_list
    except Exception as e:
        print(f"Error converting string to list: {e}")
        return []


def make_int_list_from_string(s: str) -> list[int]:
    """
    Converts a string representation of a list of integers into an actual list of integers.
    :param s: A string representation of a list of integers
    :type s: str
    :return: List of integers
    :rtype: list[int]
    """
    try:
        new_list = []
        for x in s.strip("[]").split(","):
            new_list.append(int(x.strip()))
        return new_list
    except Exception as e:
        print(f"Error converting string to list: {e}")
        return []


def make_str_int_tuple_from_string(s: str) -> tuple[str, str, int, int]:
    """
    Converts a string representation of a tuple into an actual tuple.
    :param s: String representation of a tuple in the format "[str, str, int, int]"
    :type s: str
    :return: Tuple containing two strings and two integers
    :rtype: tuple[str, str, int, int]
    """
    try:
        parts = s.strip("[]").split(",")
        if len(parts) != 4:
            raise ValueError("String does not contain exactly 4 parts.")
        return parts[0].strip(), parts[1].strip(), int(parts[2].strip()), int(parts[3].strip())
    except Exception:
        print_error(f"Error converting string to tuple: {s}")
        return "", "", -1, -1


def create_random_ssg(number_of_vertices: int, number_of_transitions: int, number_of_target_vertices: int, no_additional_selfloops: bool = False, debug: bool = GLOBAL_DEBUG) -> SimpleStochasticGame:
    """
    Create a new SSG with random parameters.
    :param number_of_vertices: Number of vertices in the SSG
    :type number_of_vertices: int
    :param number_of_transitions: Number of outgoing transitions for each vertex
    :type number_of_transitions: int
    :param number_of_target_vertices: Number of target vertices in the SSG
    :type number_of_target_vertices: int
    :param no_additional_selfloops: Whether to add additional self-loops
    :type no_additional_selfloops: bool
    :param debug: Whether to print debug information
    :type debug: bool
    :return: SSG with random parameters
    :rtype: SimpleStochasticGame
    """
    if debug:
        start_time = time.time()

    vertices: dict[str, SsgVertex] = dict()
    for i in range(number_of_vertices):
        vertices[f"vertex_{i}"] = SsgVertex(f"vertex_{i}", bool(random.randint(0, 1)), False)
    target_vertices = random.sample(list(vertices.values()), number_of_target_vertices)
    for vertex in target_vertices:
        vertex.is_target = True
    init_vertex = random.choice(list(vertices.values()))
    transitions: dict[tuple[SsgVertex, str], SsgTransition] = dict()
    action = 0
    for vertex in vertices.values():
        for i in range(number_of_transitions):
            if i == 0:
                random_vertex1 = random.choice(list(vertices.values()))
                random_vertex2 = random.choice(list(vertices.values()))
                while random_vertex2 == random_vertex1:
                    random_vertex2 = random.choice(list(vertices.values()))
                transitions[(vertex, f"action_{i}")] = SsgTransition(start_vertex=vertex, end_vertices={(0.5, random_vertex1), (0.5, random_vertex2)}, action=f"action_{i}")
            else:
                if random.randint(0, 1) == 1:
                    transitions[(vertex, f"action_{i}")] = SsgTransition(start_vertex=vertex, end_vertices={(1.0, random.choice(list(vertices.values())))}, action=f"action_{i}")
                else:
                    random_vertex1 = random.choice(list(vertices.values()))
                    random_vertex2 = random.choice(list(vertices.values()))
                    while random_vertex2 == random_vertex1:
                        random_vertex2 = random.choice(list(vertices.values()))
                    transitions[(vertex, f"action_{i}")] = SsgTransition(start_vertex=vertex, end_vertices={(0.5, random_vertex1), (0.5, random_vertex2)}, action=f"action_{i}")
    if no_additional_selfloops:
        vertices["eve_sink"] = SsgVertex("eve_sink", True, False)
        vertices["adam_sink"] = SsgVertex("adam_sink", False, False)
        transitions[(vertices["eve_sink"], str(action))] = SsgTransition(vertices["eve_sink"], {(1.0, vertices["eve_sink"])}, str(action))
        transitions[(vertices["adam_sink"], str(action))] = SsgTransition(vertices["adam_sink"], {(1.0, vertices["adam_sink"])}, str(action))
        for vertex in vertices.values():
            if vertex.name != "eve_sink" and vertex.name != "adam_sink":
                if is_deadlock_vertex(vertex, transitions):
                    if vertex.is_eve:
                        transitions[(vertex, str(action))] = SsgTransition(vertex, {(1.0, vertices["adam_sink"])}, "b")
                    else:
                        transitions[(vertex, str(action))] = SsgTransition(vertex, {(1.0, vertices["eve_sink"])}, "b")
    if debug:
        print_debug(f"Created random SSG with {len(vertices)} vertices and {len(transitions)} transitions in {time.time() - start_time:.2f} seconds.")

    return SimpleStochasticGame(vertices, transitions, init_vertex)


def create_binary_tree_ssg(number_of_layers: int, share_of_target_vertices: float, debug: bool = GLOBAL_DEBUG) -> SimpleStochasticGame:
    """
    Create a binary tree SSG with the given number of layers and target vertices.
    :param number_of_layers: Number of layers in the binary tree
    :type number_of_layers: int
    :param share_of_target_vertices: Share of target vertices in the binary tree
    :type share_of_target_vertices: float
    :param debug: Whether to print debug information
    :type debug: bool
    :return: Binary tree SSG
    :rtype: SimpleStochasticGame
    """
    if debug:
        start_time = time.time()
    vertices = {}
    transitions = {}
    leaves = []
    for layer in range(number_of_layers):
        for i in range(2 ** layer):
            vertex_name = f"layer_{layer}_vertex_{i}"
            vertices[vertex_name] = SsgVertex(vertex_name, False, False)
            if random.randint(0, 1) == 1:
                vertices[vertex_name].is_eve = True

            if layer > 0:
                parent_index = i // 2
                parent_vertex_name = f"layer_{layer - 1}_vertex_{parent_index}"

                if i % 2 != 0:
                    transitions[(vertices[parent_vertex_name], "a")] = SsgTransition(vertices[parent_vertex_name], {(0.5, vertices[vertex_name]), (0.5, vertices[f"layer_{layer}_vertex_{i - 1}"])}, "a")
            if layer == number_of_layers - 1:
                leaves.append(vertices[vertex_name])
    if 0 <= share_of_target_vertices <= 1:
        target_vertices = random.sample(leaves, round(share_of_target_vertices * len(leaves)))
    else:
        target_vertices = random.sample(leaves, len(leaves)//2)
    for vertex in target_vertices:
        vertex.is_target = True
    init_vertex = vertices["layer_0_vertex_0"]
    if debug:
        print_debug(f"Created binary tree SSG with {len(vertices)} vertices and {len(transitions)} transitions in {time.time() - start_time:.2f} seconds.")
    return SimpleStochasticGame(vertices, transitions, init_vertex)


def create_complete_graph_ssg(number_of_vertices: int, number_of_target_vertices: int, debug: bool = GLOBAL_DEBUG) -> SimpleStochasticGame:
    """
    Create a complete graph SSG with the given number of vertices and target vertices.
    :param number_of_vertices: Number of vertices in the SSG
    :type number_of_vertices: int
    :param number_of_target_vertices: Number of target vertices in the SSG
    :type number_of_target_vertices: int
    :param debug: Whether to print debug information
    :type debug: bool
    :return: Complete graph SSG
    :rtype: SimpleStochasticGame
    """
    vertices = {}
    transitions = {}
    for i in range(number_of_vertices):
        vertex_name = f"vertex_{i}"
        vertices[vertex_name] = SsgVertex(vertex_name, False, False)
        if random.randint(0, 1) == 1:
            vertices[vertex_name].is_eve = True
    target_vertices = random.sample(list(vertices.values()), number_of_target_vertices)
    for vertex in target_vertices:
        vertex.is_target = True
    action = 0
    for start_vertex in vertices.values():
        for end_vertex in vertices.values():
            transitions[(start_vertex, str(action))] = SsgTransition(start_vertex, {(1.0, end_vertex)}, str(action))
            action += 1
    init_vertex = vertices["vertex_0"]
    if debug:
        print_debug(f"Created complete graph SSG with {len(vertices)} vertices and {len(transitions)} transitions.")
    return SimpleStochasticGame(vertices, transitions, init_vertex)


def create_chain_ssg(number_of_vertices: int, debug: bool = GLOBAL_DEBUG) -> SimpleStochasticGame:
    """
    Create a chain SSG with the given number of vertices.
    :param number_of_vertices: Number of vertices in the SSG
    :type number_of_vertices: int
    :param debug: Whether to print debug information
    :type debug: bool
    :return: Chain SSG
    :rtype: SimpleStochasticGame
    """
    if debug is None:
        debug = GLOBAL_DEBUG
    if debug:
        start_time = time.time()
    vertices = {}
    transitions = {}
    for i in range(number_of_vertices):
        vertex_name = f"vertex_{i}"
        vertices[vertex_name] = SsgVertex(vertex_name, False, False)
        if random.randint(0, 1) == 1:
            vertices[vertex_name].is_eve = True
        if i == number_of_vertices - 1:
            vertices[vertex_name].is_target = True

        if i > 0:
            transitions[(vertices[f"vertex_{i-1}"], "a")] = SsgTransition(vertices[f"vertex_{i - 1}"], {(0.5, vertices[vertex_name]), (0.5, vertices["vertex_0"])}, "a")
    init_vertex = vertices["vertex_0"]
    if debug:
        print_debug(f"Created chain SSG with {len(vertices)} vertices and {len(transitions)} transitions in {time.time() - start_time:.2f} seconds.")
    return SimpleStochasticGame(vertices, transitions, init_vertex)


def create_empty_ssg(number_of_vertices: int, debug: bool = GLOBAL_DEBUG) -> SimpleStochasticGame:
    """
    Create an empty SSG with the given number of vertices.
    :param number_of_vertices: Number of vertices in the SSG
    :type number_of_vertices: int
    :param debug: Whether to print debug information
    :type debug: bool
    :return: Empty SSG
    :rtype: SimpleStochasticGame
    """
    if debug:
        start_time = time.time()
    vertices = {}
    transitions = {}
    for i in range(number_of_vertices):
        vertex_name = f"vertex_{i}"
        vertices[vertex_name] = SsgVertex(vertex_name, False, False)
        if random.randint(0, 1) == 1:
            vertices[vertex_name].is_eve = True

    init_vertex = vertices["vertex_0"]
    if debug:
        print_debug(f"Created empty SSG with {len(vertices)} vertices and {len(transitions)} transitions in {time.time() - start_time:.2f} seconds.")
    return SimpleStochasticGame(vertices, transitions, init_vertex)


def print_smg_stats(smg_file: str, debug: bool = GLOBAL_DEBUG, use_global_path: bool = False) -> None:
    """
    Print the statistics of an SMG file.
    :param smg_file: Path to the SMG file
    :type smg_file: str
    :param debug: Whether to print debug information
    :type debug: bool
    :param use_global_path: Whether to use the global path for the SMG file
    :type use_global_path: bool
    """
    states, transitions, constr_time = check_smg_stats(smg_file=smg_file, debug=debug, use_global_path=use_global_path)
    output = f"SMG file: {smg_file}\n\n"
    if states != -1:
        output += f"\tNumber of States: \t\t{states}\n"
    else:
        output += "\tNumber of States: \t\tCould not be evaluated\n"
    if transitions != -1:
        output += f"\tNumber of Transitions: \t{transitions}\n"
    else:
        output += "\tNumber of Transitions: \tCould not be evaluated\n"
    if constr_time != -1:
        output += f"\tConstruction Time: \t\t{constr_time} seconds"
    else:
        output += "\tConstruction Time: \t\tCould not be evaluated"
    print(output)


def benchmark_multiple_ssgs(ssg_count: int, ssg_type: str, size_param: int, save_results: bool = None, result_path: str = None, use_global_path: bool = False, force: bool = True, debug: bool = GLOBAL_DEBUG) -> tuple[list[float], list[float], list[float], list[float], list[int], list[int], list[int], list[int], tuple[str, str, int, int]]:
    """
    Benchmark the creation and property checking of multiple SSGs.
    :param ssg_count: Number of SSGs to create
    :type ssg_count: int
    :param ssg_type: Type of SSG to create (random, binary, empty)
    :type ssg_type: str
    :param size_param: Size parameter for the SSG
    :type size_param: int
    :param save_results: Whether to write the benchmark results to a file
    :type save_results: bool
    :param result_path: Path to save the benchmark results
    :type result_path: str
    :param use_global_path: Whether to use the global path for the SMG file
    :type use_global_path: bool
    :param force: Whether to force the creation of the SSG
    :type force: bool
    :param debug: Whether to print debug information
    :type debug: bool
    :return: Tuple containing the average transformation and property checking times for both versions
    :rtype: tuple[list[float], list[float], list[float], list[float], list[int], list[int], list[int], list[int], tuple[str, str, int, int]]
    """
    import time
    all_v1_trans_times = []
    all_v2_trans_times = []
    all_v1_prop_times = []
    all_v2_prop_times = []
    all_v1_vertices = []
    all_v2_vertices = []
    all_v1_transitions = []
    all_v2_transitions = []

    if result_path is None:
        result_path = f"benchmark_results_normal_{ssg_count}_{ssg_type}_{size_param}.txt"
    if use_global_path:
        result_path = os.path.join(GLOBAL_IN_OUT_PATH, result_path)
    if save_results is None:
        save_results = False if not force and os.path.exists(result_path) and os.path.getsize(result_path) > 0 else True
    if debug:
        match ssg_type:
            case "random":
                print_debug(f"Creating {ssg_count} random SSGs with {size_param} vertices and {5 * size_param} transitions.")
            case "random_no_additional_selfloops":
                print_debug(f"Creating {ssg_count} random SSGs with {size_param} vertices and {5 * size_param} transitions without additional self-loops.")
            case "binary":
                print_debug(f"Creating {ssg_count} binary tree SSGs with {size_param} layers and {round(0.3 * (2 ** size_param) / 2)} target vertices.")
            case "complete":
                print_debug(f"Creating {ssg_count} complete graph SSGs with {size_param} vertices and {max(1, size_param // 10)} target vertices.")
            case "chain":
                print_debug(f"Creating {ssg_count} chain SSGs with {size_param} vertices.")
            case _:
                print_debug(f"Creating {ssg_count} empty SSGs with {size_param} vertices.")
    for i in range(ssg_count):
        if debug:
            print_debug(f"{i}/{ssg_count} SSGs created and evaluated.")
        if ssg_type == "random":
            ssg_i = create_random_ssg(size_param, 5 * size_param, max(1, size_param // 10), no_additional_selfloops=False)
        elif ssg_type == "random_no_additional_selfloops":
            ssg_i = create_random_ssg(size_param, 5 * size_param, max(1, size_param // 10), no_additional_selfloops=True)
        elif ssg_type == "binary":
            ssg_i = create_binary_tree_ssg(size_param, 0.3)
        elif ssg_type == "complete":
            ssg_i = create_complete_graph_ssg(size_param, max(1, size_param // 10))
        elif ssg_type == "chain":
            ssg_i = create_chain_ssg(size_param)
        else:
            ssg_i = create_empty_ssg(size_param)

        start_v1 = time.perf_counter()
        smg_v1 = ssg_to_smgspec(ssg_i, version=1)
        trans_v1_time = time.perf_counter() - start_v1
        save_smg_file(smg_v1, f"ssg_{i+1}_v1.smg", use_global_path=True, force=True)
        start_v1_prop = time.perf_counter()
        check_target_reachability(f"ssg_{i+1}_v1.smg", print_probabilities=False, use_global_path=True)
        prop_v1_time = time.perf_counter() - start_v1_prop
        vert_v1, trans_v1, build_time1 = check_smg_stats(f"ssg_{i + 1}_v1.smg", use_global_path=True)

        start_v2 = time.perf_counter()
        smg_v2 = ssg_to_smgspec(ssg_i, version=3)
        trans_v2_time = time.perf_counter() - start_v2
        save_smg_file(smg_v2, f"ssg_{i+1}_v2.smg", use_global_path=True, force=True)
        start_v2_prop = time.perf_counter()
        check_target_reachability(f"ssg_{i+1}_v2.smg", print_probabilities=False, use_global_path=True)
        prop_v2_time = time.perf_counter() - start_v2_prop
        vert_v2, trans_v2, build_time2 = check_smg_stats(f"ssg_{i + 1}_v2.smg", use_global_path=True)

        if use_global_path:
            smg_v1_path = os.path.join(GLOBAL_IN_OUT_PATH, f"ssg_{i+1}_v1.smg")
            smg_v2_path = os.path.join(GLOBAL_IN_OUT_PATH, f"ssg_{i+1}_v2.smg")
        else:
            smg_v1_path = f"ssg_{i+1}_v1.smg"
            smg_v2_path = f"ssg_{i+1}_v2.smg"
        if trans_v1_time == 0.0 or trans_v2_time == 0.0 or prop_v1_time == 0.0 or prop_v2_time == 0.0:
            print_error(f"Error: Transformation or property checking time is 0.0 for SSG {i+1}.")
        os.remove(smg_v1_path)
        os.remove(smg_v2_path)

        all_v1_trans_times.append(trans_v1_time)
        all_v2_trans_times.append(trans_v2_time)
        all_v1_prop_times.append(prop_v1_time)
        all_v2_prop_times.append(prop_v2_time)
        all_v1_vertices.append(vert_v1)
        all_v2_vertices.append(vert_v2)
        all_v1_transitions.append(trans_v1)
        all_v2_transitions.append(trans_v2)

    if debug:
        print_debug(f"{ssg_count}/{ssg_count} SSGs created and evaluated.")
    if save_results:
        output = str(all_v1_trans_times) + "\n"
        output += str(all_v2_trans_times) + "\n"
        output += str(all_v1_prop_times) + "\n"
        output += str(all_v2_prop_times) + "\n"
        output += str(all_v1_vertices) + "\n"
        output += str(all_v2_vertices) + "\n"
        output += str(all_v1_transitions) + "\n"
        output += str(all_v2_transitions) + "\n"
        output += f"[norm, {ssg_type}, {ssg_count}, {size_param}]" + "\n"
        with open(result_path, "w") as f:
            f.write(output)

    return all_v1_trans_times, all_v2_trans_times, all_v1_prop_times, all_v2_prop_times, all_v1_vertices, all_v2_vertices, all_v1_transitions, all_v2_transitions, ("norm", ssg_type, ssg_count, size_param)


def _iteration_worker(q, ssg_type, i, use_global_path):
    """
    Worker function to run a single benchmark iteration and return results via Queue.
    :param q: Queue to put the results into
    :type q: Queue
    :param ssg_type: Type of SSG to create (random, binary, empty)
    :type ssg_type: str
    :param i: Index of the SSG to create
    :type i: int
    :param use_global_path: Whether to use the global path for the SMG file
    :type use_global_path: bool
    """
    try:
        result = single_iteration_for_exponential_benchmark(ssg_type, i, use_global_path)
        q.put(result)
    except Exception as e:
        q.put(e)


def single_iteration_for_exponential_benchmark(ssg_type: str, i: int, use_global_path: bool = True) -> tuple[float, float, float, float, int, int, int, int, str, str, int]:
    """
    Run a single iteration of the benchmark for a specific SSG type and index.
    :param ssg_type: Type of SSG to create
    :type ssg_type: str
    :param i: Iterator for the size of the SSG
    :type i: int
    :param use_global_path: Whether to use the global path for the SMG file
    :type use_global_path: bool
    :return: Tuple containing the transformation and property checking times for both versions, number of vertices and transitions, and paths to the SMG files
    :rtype: tuple[float, float, float, float, int, int, int, int, str, str, int]
    """
    if ssg_type == "binary":
        size_param = i + 2
    else:
        size_param = (2 ** (i + 1))
    if ssg_type == "random":
        ssg_i = create_random_ssg(size_param, math.ceil(0.1 * size_param), max(1, size_param // 10),
                                  no_additional_selfloops=False)
    elif ssg_type == "random_no_additional_selfloops":
        ssg_i = create_random_ssg(size_param, 5 * size_param, max(1, size_param // 10),
                                  no_additional_selfloops=True)
    elif ssg_type == "binary":
        ssg_i = create_binary_tree_ssg(size_param, 0.3)
    elif ssg_type == "complete":
        ssg_i = create_complete_graph_ssg(size_param, max(1, size_param // 10))
    elif ssg_type == "chain":
        ssg_i = create_chain_ssg(size_param)
    else:
        ssg_i = create_empty_ssg(size_param)

    start_v1 = time.perf_counter()
    smg_v1 = ssg_to_smgspec(ssg_i, version=1)
    trans_v1_time = time.perf_counter() - start_v1
    print_debug(f"Transformation with version1 took {trans_v1_time} seconds.")
    save_smg_file(smg_v1, f"ssg_{i + 1}_v1.smg", use_global_path=use_global_path, force=True)
    start_v1_prop = time.perf_counter()
    check_target_reachability(f"ssg_{i + 1}_v1.smg", print_probabilities=False, use_global_path=use_global_path)
    prop_v1_time = time.perf_counter() - start_v1_prop
    print_debug(f"Property checking with version1 took {prop_v1_time} seconds.")
    vert_v1, trans_v1, build_time1 = check_smg_stats(f"ssg_{i + 1}_v1.smg", use_global_path=use_global_path)

    start_v2 = time.perf_counter()
    smg_v2 = ssg_to_smgspec(ssg_i, version=2)
    trans_v2_time = time.perf_counter() - start_v2
    print_debug(f"Transformation with version2 took {trans_v2_time} seconds.")
    save_smg_file(smg_v2, f"ssg_{i + 1}_v2.smg", use_global_path=use_global_path, force=True)
    start_v2_prop = time.perf_counter()
    check_target_reachability(f"ssg_{i + 1}_v2.smg", print_probabilities=False, use_global_path=use_global_path)
    prop_v2_time = time.perf_counter() - start_v2_prop
    print_debug(f"Property checking with version2 took {prop_v2_time} seconds.")
    vert_v2, trans_v2, build_time2 = check_smg_stats(f"ssg_{i + 1}_v2.smg", use_global_path=use_global_path)

    if use_global_path:
        smg_v1_path = os.path.join(GLOBAL_IN_OUT_PATH, f"ssg_{i + 1}_v1.smg")
        smg_v2_path = os.path.join(GLOBAL_IN_OUT_PATH, f"ssg_{i + 1}_v2.smg")
    else:
        smg_v1_path = f"ssg_{i + 1}_v1.smg"
        smg_v2_path = f"ssg_{i + 1}_v2.smg"
    if trans_v1_time == 0.0 or trans_v2_time == 0.0 or prop_v1_time == 0.0 or prop_v2_time == 0.0:
        print_error(f"Error: Transformation or property checking time is 0.0 for SSG {i + 1}.")

    return trans_v1_time, trans_v2_time, prop_v1_time, prop_v2_time, vert_v1, vert_v2, trans_v1, trans_v2, smg_v1_path, smg_v2_path, size_param


def benchmark_exponential_ssgs(ssg_type: str, time_per_iteration: int = 120, save_results: bool = None, result_path: str = None, use_global_path: bool = True, force: bool = True, debug: bool = GLOBAL_DEBUG) -> tuple[list[float], list[float], list[float], list[float], list[int], list[int], list[int], list[int], tuple[str, str, int, int]]:
    """
    Benchmark the creation and property checking of multiple SSGs.
    :param ssg_type: Type of SSG to create (random, binary, empty)
    :type ssg_type: str
    :param time_per_iteration: Time in seconds for each iteration
    :type time_per_iteration: int
    :param save_results: Whether to write the benchmark results to a file
    :type save_results: bool
    :param result_path: Path to save the benchmark results
    :type result_path: str
    :param use_global_path: Whether to use the global path for the SMG file
    :type use_global_path: bool
    :param force: Whether to force the creation of the SSG
    :type force: bool
    :param debug: Whether to print debug information
    :type debug: bool
    :return: Tuple containing the average transformation and property checking times for both versions
    :rtype: tuple[list[float], list[float], list[float], list[float], list[int], list[int], list[int], list[int], tuple[str, str, int, int]]
    """

    all_v1_trans_times = []
    all_v2_trans_times = []
    all_v1_prop_times = []
    all_v2_prop_times = []
    all_v1_vertices = []
    all_v2_vertices = []
    all_v1_transitions = []
    all_v2_transitions = []
    if result_path is None:
        result_path = f"benchmark_results_exponential_{ssg_type}_max_{time_per_iteration}.txt"
    if use_global_path:
        result_path = os.path.join(GLOBAL_IN_OUT_PATH, result_path)
    if save_results is None:
        save_results = False if not force and os.path.exists(result_path) and os.path.getsize(result_path) > 0 else True
    if debug:
        match ssg_type:
            case "random":
                print_debug(
                    f"Creating random SSGs that grow exponentially until timeout of {time_per_iteration} seconds.")
            case "random_no_additional_selfloops":
                print_debug(
                    f"Creating random SSGs without additional self-loops that grow exponentially until timeout of {time_per_iteration} seconds.")
            case "binary":
                print_debug(
                    f"Creating binary tree SSGs that grow exponentially until timeout of {time_per_iteration} seconds.")
            case "complete":
                print_debug(
                    f"Creating complete graph SSGs that grow exponentially until timeout of {time_per_iteration} seconds.")
            case "chain":
                print_debug(f"Creating chain SSGs that grow exponentially until timeout of {time_per_iteration} seconds.")
            case _:
                print_debug(f"Creating empty SSGs that grow exponentially until timeout of {time_per_iteration} seconds.")
    i = 0
    while True:
        q = Queue()
        p = Process(target=_iteration_worker, args=(q, ssg_type, i, use_global_path))
        start_time = time.perf_counter()
        p.start()
        p.join(timeout=time_per_iteration)
        end_time = time.perf_counter()

        if p.is_alive():
            if debug:
                print_debug(f"Timeout of {time_per_iteration} seconds reached for SSG {i + 1}.")
            kill_process_and_children(p.pid)
            p.join()
            try:
                if use_global_path:
                    smg_v1_path = os.path.join(GLOBAL_IN_OUT_PATH, f"ssg_{i + 1}_v1.smg")
                    smg_v2_path = os.path.join(GLOBAL_IN_OUT_PATH, f"ssg_{i + 1}_v2.smg")
                else:
                    smg_v1_path = f"ssg_{i + 1}_v1.smg"
                    smg_v2_path = f"ssg_{i + 1}_v2.smg"
                os.remove(smg_v1_path)
                os.remove(smg_v2_path)
            except FileNotFoundError:
                pass
            break
        try:
            result = q.get_nowait()
        except pyqueue.Empty:
            print_warning(f"No result received from subprocess for SSG {i + 1}.")
            break

        if isinstance(result, Exception):
            print_warning(f"Subprocess failed with exception: {result}")
            break

        (trans_v1_time, trans_v2_time, prop_v1_time, prop_v2_time,
         vert_v1, vert_v2, trans_v1, trans_v2,
         smg_v1_path, smg_v2_path, size_param) = result

        if vert_v1 < 0 or vert_v2 < 0 or trans_v1 < 0 or trans_v2 < 0:
            print_warning(f"Negative values for vertices or transitions in SSG {i + 1}.")
            break

        if debug:
            print_debug(f"SSG {i + 1} with size parameter {size_param} successfully completed in {end_time-start_time:.2f} seconds.")
            print_debug(f"Preparing SSG {i + 2}.")

        # Remove temporary .smg files
        try:
            os.remove(smg_v1_path)
            os.remove(smg_v2_path)
        except FileNotFoundError:
            pass

        # Collect results
        all_v1_trans_times.append(trans_v1_time)
        all_v2_trans_times.append(trans_v2_time)
        all_v1_prop_times.append(prop_v1_time)
        all_v2_prop_times.append(prop_v2_time)
        all_v1_vertices.append(vert_v1)
        all_v2_vertices.append(vert_v2)
        all_v1_transitions.append(trans_v1)
        all_v2_transitions.append(trans_v2)

        i += 1
    if ssg_type == "binary":
        size_param = i + 2
    else:
        size_param = (2 ** (i + 1))
    if save_results:
        output = str(all_v1_trans_times) + "\n"
        output += str(all_v2_trans_times) + "\n"
        output += str(all_v1_prop_times) + "\n"
        output += str(all_v2_prop_times) + "\n"
        output += str(all_v1_vertices) + "\n"
        output += str(all_v2_vertices) + "\n"
        output += str(all_v1_transitions) + "\n"
        output += str(all_v2_transitions) + "\n"
        output += f"[ex, {ssg_type}, {size_param}, {time_per_iteration}]" + "\n"
        with open(result_path, "w") as f:
            f.write(output)

    return all_v1_trans_times, all_v2_trans_times, all_v1_prop_times, all_v2_prop_times, all_v1_vertices, all_v2_vertices, all_v1_transitions, all_v2_transitions, ("ex", ssg_type, size_param, time_per_iteration)


def read_benchmark_results(file_path: str, use_global_path: bool = True) -> tuple[list[float], list[float], list[float], list[float], list[int], list[int], list[int], list[int], tuple[str, str, int, int]]:
    """
    Read benchmark results from a file.
    :param file_path: Path to the benchmark results file
    :type file_path: str
    :param use_global_path: Whether to use the global path for the file
    :type use_global_path: bool
    :return: Tuple containing the benchmark results
    :rtype: tuple[list[float], list[float], list[float], list[float], list[int], list[int], list[int], list[int]]
    """
    if use_global_path:
        file_path = os.path.join(GLOBAL_IN_OUT_PATH, file_path)
    with open(file_path, "r") as f:
        content = f.readlines()
    if len(content) < 8:
        raise ValueError(f"File {file_path} does not contain enough data. Expected 8 lines, got {len(content)}.")
    return make_float_list_from_string(content[0].replace("\n", "")), make_float_list_from_string(content[1].replace("\n", "")), make_float_list_from_string(content[2].replace("\n", "")), make_float_list_from_string(content[3].replace("\n", "")), make_int_list_from_string(content[4].replace("\n", "")), make_int_list_from_string(content[5].replace("\n", "")), make_int_list_from_string(content[6].replace("\n", "")), make_int_list_from_string(content[7].replace("\n", "")), make_str_int_tuple_from_string(content[8].replace("\n", ""))


def plot_benchmark_results(all_v1_trans_times: list[float], all_v2_trans_times: list[float], all_v1_prop_times: list[float], all_v2_prop_times: list[float], all_v1_vertices: list[int], all_v2_vertices: list[int], all_v1_transitions: list[int], all_v2_transitions: list[int], benchmark_info: tuple[str, str, int, int], show_times: bool = True, show_stats: bool = True, plot_name: str = None, save_plots: bool = False, use_global_path: bool = True) -> None:
    """
    Plot the benchmark results
    :param all_v1_trans_times: List of all transformation times for version 1
    :type all_v1_trans_times: [float]
    :param all_v2_trans_times: List of all transformation times for version 2
    :type all_v2_trans_times: [float]
    :param all_v1_prop_times: List of all property checking times for version 1
    :type all_v1_prop_times: [float]
    :param all_v2_prop_times: List of all property checking times for version 2
    :type all_v2_prop_times: [float]
    :param all_v1_vertices: List of all vertices counts for version 1
    :type all_v1_vertices: [int]
    :param all_v2_vertices: List of all vertices counts for version 2
    :type all_v2_vertices: [int]
    :param all_v1_transitions: List of all transitions counts for version 1
    :type all_v1_transitions: [int]
    :param all_v2_transitions: List of all transitions counts for version 2
    :type all_v2_transitions: [int]
    :param benchmark_info: Tuple containing the benchmark information
    :type benchmark_info: (str, str, int, int)
    :param show_times: Whether to show the transformation and property checking times plot
    :type show_times: bool
    :param show_stats: Whether to show the statistics plot
    :type show_stats: bool
    :param plot_name: Name of the plot file
    :type plot_name: str
    :param save_plots: Whether to save the plots
    :type save_plots: bool
    :param use_global_path: Whether to use the global path for the plot file
    :type use_global_path: bool
    """
    with contextlib.redirect_stdout(io.StringIO()):
        matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    import numpy as np

    x1 = np.array(all_v1_trans_times)
    y1 = np.array(all_v2_trans_times)
    x2 = np.array(all_v1_prop_times)
    y2 = np.array(all_v2_prop_times)
    x3 = np.array(all_v1_vertices)
    y3 = np.array(all_v2_vertices)
    x4 = np.array(all_v1_transitions)
    y4 = np.array(all_v2_transitions)

    mean_v1_tt = np.mean(x1)
    std_v1_tt = np.std(x1)
    mean_v2_tt = np.mean(y1)
    std_v2_tt = np.std(y1)
    mean_v1_pt = np.mean(x2)
    std_v1_pt = np.std(x2)
    mean_v2_pt = np.mean(y2)
    std_v2_pt = np.std(y2)
    mean_v1_v = np.mean(x3)
    std_v1_v = np.std(x3)
    mean_v2_v = np.mean(y3)
    std_v2_v = np.std(y3)
    mean_v1_t = np.mean(x4)
    std_v1_t = np.std(x4)
    mean_v2_t = np.mean(y4)
    std_v2_t = np.std(y4)

    mask_above1 = y1 > x1
    mask_below1 = ~mask_above1
    mask_above2 = y2 > x2
    mask_below2 = ~mask_above2
    mask_above3 = y3 > x3
    mask_below3 = ~mask_above3
    mask_above4 = y4 > x4
    mask_below4 = ~mask_above4

    better_v1_tt_count = 0
    for i in range(len(x1)):
        if x1[i] < y1[i]:
            better_v1_tt_count += 1

    better_v1_pc_count = 0
    for i in range(len(x2)):
        if x2[i] < y2[i]:
            better_v1_pc_count += 1

    better_v1_v_count = 0
    for i in range(len(x3)):
        if x3[i] < y3[i]:
            better_v1_v_count += 1

    better_v1_t_count = 0
    for i in range(len(x4)):
        if x4[i] < y4[i]:
            better_v1_t_count += 1

    if plot_name is None:
        if benchmark_info[0] == "norm":
            plot_name = f"benchmark_results_normal_{benchmark_info[1]}_{benchmark_info[2]}_{benchmark_info[3]}"
        elif benchmark_info[0] == "ex":
            plot_name = f"benchmark_results_exponential_{benchmark_info[1]}_{benchmark_info[2]}_{benchmark_info[3]}"
        else:
            raise ValueError(f"Unknown benchmark type: {benchmark_info[0]}. Expected \'norm\' or \'ex\'.")

    fig, axs = plt.subplots(1, 2, figsize=(12, 6), num=plot_name + "_time_comparison")
    fig.suptitle("Benchmark Transformation vs. Property Checking Time")

    # --- Plot 1: Transformation Time ---
    axs[0].set_xscale('log')
    axs[0].set_yscale('log')
    axs[0].scatter(x1[mask_above1], y1[mask_above1], color='red', label='v1 faster than v2')
    axs[0].scatter(x1[mask_below1], y1[mask_below1], color='blue', label='v2 faster than v1')
    axs[0].plot(x1, x1, linestyle='-', color='black', label='v1 and v2 equal', )
    axs[0].plot(x1, 2 * x1, linestyle='--', color='#808080')
    axs[0].plot(x1, 0.5 * x1, linestyle='--', color='#808080')
    axs[0].set_xlabel("v1 Transformation Time [s]")
    axs[0].set_ylabel("v2 Transformation Time [s]")
    axs[0].grid(True, which='major', ls='--')
    axs[0].legend()
    axs[0].set_title(f"Transformation | v1 better in {better_v1_tt_count / len(x1) * 100:.2f}%")

    # --- Plot 2: Property Checking Time ---
    axs[1].set_xscale('log')
    axs[1].set_yscale('log')
    axs[1].scatter(x2[mask_above2], y2[mask_above2], color='red', label='v1 faster than v2')
    axs[1].scatter(x2[mask_below2], y2[mask_below2], color='blue', label='v2 faster than v1')
    axs[1].plot(x2, x2, linestyle='-', color='black', label='v1 and v2 equal')
    axs[1].plot(x2, 2 * x2, linestyle='--', color='#808080')
    axs[1].plot(x2, 0.5 * x2, linestyle='--', color='#808080')
    axs[1].set_xlabel("v1 Property Checking Time [s]")
    axs[1].set_ylabel("v2 Property Checking Time [s]")
    axs[1].grid(True, which='major', ls='--')
    axs[1].legend()
    axs[1].set_title(f"Property Check | v1 better in {better_v1_pc_count / len(x2) * 100:.2f}%")

    # --- Statistic Info ---
    fig.text(0.5, 0.01,
             f"v1 TT: μ={mean_v1_tt:.5f}, σ={std_v1_tt:.5f} | "
             f"v2 TT: μ={mean_v2_tt:.5f}, σ={std_v2_tt:.5f} || "
             f"v1 PT: μ={mean_v1_pt:.5f}, σ={std_v1_pt:.5f} | "
             f"v2 PT: μ={mean_v2_pt:.5f}, σ={std_v2_pt:.5f}",
             ha='center', fontsize=9)

    fig.tight_layout(rect=(0, 0.05, 1, 0.95))

    if save_plots:
        filename = f"{plot_name}_times_combined.png"
        if use_global_path:
            filename = os.path.join(GLOBAL_IN_OUT_PATH, "benchmarks", "exponential", filename)
        fig.savefig(filename)

    if not show_times:
        plt.close(fig)

    fig_stat, axs = plt.subplots(1, 2, figsize=(12, 6), num=plot_name + "_stats_comparison")
    fig_stat.suptitle("Benchmark Graph Statistics (Vertices vs. Transitions)")

    # Plot: Vertices
    axs[0].set_xscale('log')
    axs[0].set_yscale('log')
    axs[0].scatter(x3[mask_above3], y3[mask_above3], color='red', label='#v with v1 < #v with v2')
    axs[0].scatter(x3[mask_below3], y3[mask_below3], color='blue', label='#v with v2 < #v with v1')
    axs[0].plot(x3, x3, linestyle='-', color='black', label='#v with v1 = #v with v2')
    axs[0].plot(x3, 2 * x3, linestyle='--', color='#808080')
    axs[0].plot(x3, 0.5 * x3, linestyle='--', color='#808080')
    axs[0].set_xlabel("v1 Vertices")
    axs[0].set_ylabel("v2 Vertices")
    axs[0].set_title(f"Vertices | v1 less vertices than v2 in {better_v1_v_count / len(x3) * 100:.2f}% of the cases")
    axs[0].legend()
    axs[0].grid(True, which='major', ls='--')

    # Plot: Transitions
    axs[1].set_xscale('log')
    axs[1].set_yscale('log')
    axs[1].scatter(x4[mask_above4], y4[mask_above4], color='red', label='#t with v1 < #t with v2')
    axs[1].scatter(x4[mask_below4], y4[mask_below4], color='blue', label='#t with v2 < #t with v1')
    axs[1].plot(x4, x4, linestyle='-', color='black', label='#t with v1 = #t with v2')
    axs[1].plot(x4, 2 * x4, linestyle='--', color='#808080')
    axs[1].plot(x4, 0.5 * x4, linestyle='--', color='#808080')
    axs[1].set_xlabel("v1 Transitions")
    axs[1].set_ylabel("v2 Transitions")
    axs[1].set_title(f"Transitions | v1 less transitions than v2 in {better_v1_t_count / len(x4) * 100:.2f}% of the cases")
    axs[1].legend()
    axs[1].grid(True, which='major', ls='--')

    # --- Statistic Info ---
    fig_stat.text(0.5, 0.01,
                  f"v1 Vertices: μ={mean_v1_v:.2f}, σ={std_v1_v:.2f} | "
                  f"v2 Vertices: μ={mean_v2_v:.2f}, σ={std_v2_v:.2f} || "
                  f"v1 Transitions: μ={mean_v1_t:.2f}, σ={std_v1_t:.2f} | "
                  f"v2 Transitions: μ={mean_v2_t:.2f}, σ={std_v2_t:.2f}",
                  ha='center', fontsize=9)

    fig_stat.tight_layout(rect=(0, 0.05, 1, 0.95))

    if save_plots:
        filename = f"{plot_name}_stats_combined.png"
        if use_global_path:
            filename = os.path.join(GLOBAL_IN_OUT_PATH, "benchmarks", "exponential", filename)
        fig_stat.savefig(filename)

    if not show_stats:
        plt.close(fig_stat)

    if show_times or show_stats:
        plt.show()


def plot_combined_benchmark_results(benchmarks_results: list[tuple[list[float], list[float], list[float], list[float], list[int], list[int], list[int], list[int], tuple[str, str, int, int]]], show_times: bool = True, show_stats: bool = True, plot_name: str = None, save_plots: bool = False, use_global_path: bool = True, versions: tuple[int, int] = (1, 2)) -> None:
    """
    Plot combined benchmark results.
    :param benchmarks_results: The benchmark results to plot, each as a tuple containing transformation times, property checking times, vertices counts, transitions counts, and benchmark info.
    :type benchmarks_results: list[tuple[list[float], list[float], list[float], list[float], list[int], list[int], list[int], list[int], tuple[str, str, int, int]]]
    :param show_times: Whether to show the transformation and property checking times plot
    :type show_times: bool
    :param show_stats: Whether to show the statistics plot
    :type show_stats: bool
    :param plot_name: Name of the plot file
    :type plot_name: str
    :param save_plots: Whether to save the plots
    :type save_plots: bool
    :param use_global_path: Whether to use the global path for the plot file
    :type use_global_path: bool
    :param versions: Tuple containing the versions to compare (e.g., (1, 2))
    :type versions: tuple[int, int]
    :return:
    """
    with contextlib.redirect_stdout(io.StringIO()):
        matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    import numpy as np

    v1, v2 = versions[0], versions[1]

    data = []
    for benchmark_index in range(len(benchmarks_results)):
        data_i = []
        for i in range(8):
            data_i.append(np.array(benchmarks_results[benchmark_index][i]))
        data.append((data_i, benchmarks_results[benchmark_index][8][1]))

    all_v1_tt = data[0][0][1]
    all_v2_tt = data[0][0][1]
    all_v1_pt = data[0][0][2]
    all_v2_pt = data[0][0][3]
    all_v1_v = data[0][0][4]
    all_v2_v = data[0][0][5]
    all_v1_t = data[0][0][6]
    all_v2_t = data[0][0][7]
    for i in range(1, len(data)):
        all_v1_tt = np.concatenate((all_v1_tt, data[i][0][0]))
        all_v2_tt = np.concatenate((all_v2_tt, data[i][0][1]))
        all_v1_pt = np.concatenate((all_v1_pt, data[i][0][2]))
        all_v2_pt = np.concatenate((all_v2_pt, data[i][0][3]))
        all_v1_v = np.concatenate((all_v1_v, data[i][0][4]))
        all_v2_v = np.concatenate((all_v2_v, data[i][0][5]))
        all_v1_t = np.concatenate((all_v1_t, data[i][0][6]))
        all_v2_t = np.concatenate((all_v2_t, data[i][0][7]))

    ssg_type = []
    for benchmark_index in range(len(benchmarks_results)):
        for i in range(len(benchmarks_results[benchmark_index][0])):
            ssg_type.append(benchmarks_results[benchmark_index][8][1])
    ssg_type_array = np.array(ssg_type)

    colors = {"random": 'red', "random_no_additional_selfloops": 'orange', "binary": 'green', "complete": 'blue', "chain": 'purple', "empty": 'gray'}
    labels = {"random": 'Random', "random_no_additional_selfloops": 'Random (No Additional Self-Loops)', "binary": 'Binary Tree', "complete": 'Complete Graph', "chain": 'Chain', "empty": 'Empty'}

    mean_v1_tt = np.mean(all_v1_tt)
    std_v1_tt = np.std(all_v1_tt)
    mean_v2_tt = np.mean(all_v2_tt)
    std_v2_tt = np.std(all_v2_tt)
    mean_v1_pt = np.mean(all_v1_pt)
    std_v1_pt = np.std(all_v1_pt)
    mean_v2_pt = np.mean(all_v2_pt)
    std_v2_pt = np.std(all_v2_pt)
    mean_v1_v = np.mean(all_v1_v)
    std_v1_v = np.std(all_v1_v)
    mean_v2_v = np.mean(all_v2_v)
    std_v2_v = np.std(all_v2_v)
    mean_v1_t = np.mean(all_v1_t)
    std_v1_t = np.std(all_v1_t)
    mean_v2_t = np.mean(all_v2_t)
    std_v2_t = np.std(all_v2_t)

    worse_v1_tt_count = 0
    for i in range(len(all_v1_tt)):
        if all_v1_tt[i] > all_v2_tt[i]:
            worse_v1_tt_count += 1
    worse_v1_pc_count = 0
    for i in range(len(all_v1_pt)):
        if all_v1_pt[i] > all_v2_pt[i]:
            worse_v1_pc_count += 1
    worse_v1_v_count = 0
    for i in range(len(all_v1_v)):
        if all_v1_v[i] > all_v2_v[i]:
            worse_v1_v_count += 1
    worse_v1_t_count = 0
    for i in range(len(all_v1_t)):
        if all_v1_t[i] > all_v2_t[i]:
            worse_v1_t_count += 1

    if plot_name is None:
        has_normal_bechmarks = False
        has_exponential_benchmarks = False
        for benchmark_index in range(len(benchmarks_results)):
            if benchmarks_results[benchmark_index][8][0] == "norm":
                has_normal_bechmarks = True
            elif benchmarks_results[benchmark_index][8][0] == "ex":
                has_exponential_benchmarks = True
            else:
                raise ValueError(f"Unknown benchmark type: {benchmarks_results[benchmark_index][8][0]}. Expected \'norm\' or \'ex\'.")
        if has_normal_bechmarks and has_exponential_benchmarks:
            plot_name = f"benchmark_results_combined_{len(benchmarks_results)}"
        elif has_normal_bechmarks and not has_exponential_benchmarks:
            plot_name = f"benchmark_results_normal_{len(benchmarks_results)}"
        elif not has_normal_bechmarks and has_exponential_benchmarks:
            plot_name = f"benchmark_results_exponential_{len(benchmarks_results)}"
        else:
            raise ValueError("No benchmarks results provided to plot.")

    fig, axs = plt.subplots(1, 2, figsize=(12, 6), num=plot_name + "_time_comparison")
    fig.suptitle("Combined Benchmark Transformation vs. Property Checking Time")

    # --- Plot 1: Transformation Time ---
    axs[0].set_xscale('log')
    axs[0].set_yscale('log')
    for ssg_type in np.unique(ssg_type_array):
        mask = ssg_type_array == ssg_type
        axs[0].scatter(all_v1_tt[mask], all_v2_tt[mask], color=colors[ssg_type], label=labels[ssg_type])
    axs[0].plot(all_v1_tt, all_v1_tt, linestyle='-', color='black', label=f'v{v1} and v{v2} equal')
    axs[0].plot(all_v1_tt, 2 * all_v1_tt, linestyle='--', color='#808080')
    axs[0].plot(all_v1_tt, 0.5 * all_v1_tt, linestyle='--', color='#808080')
    axs[0].set_xlabel(f"v{v1} Transformation Time [s]")
    axs[0].set_ylabel(f"v{v2} Transformation Time [s]")
    axs[0].grid(True, which='major', ls='--')
    axs[0].legend()
    axs[0].set_title(f"Transformation | v{v2} better in {worse_v1_tt_count / len(all_v1_tt) * 100:.2f}%")

    # --- Plot 2: Property Checking Time ---
    axs[1].set_xscale('log')
    axs[1].set_yscale('log')
    for ssg_type in np.unique(ssg_type_array):
        mask = ssg_type_array == ssg_type
        axs[1].scatter(all_v1_pt[mask], all_v2_pt[mask], color=colors[ssg_type], label=labels[ssg_type])
    axs[1].plot(all_v1_pt, all_v1_pt, linestyle='-', color='black', label=f'v{v1} and v{v2} equal')
    axs[1].plot(all_v1_pt, 2 * all_v1_pt, linestyle='--', color='#808080')
    axs[1].plot(all_v1_pt, 0.5 * all_v1_pt, linestyle='--', color='#808080')
    axs[1].set_xlabel(f"v{v1} Property Checking Time [s]")
    axs[1].set_ylabel(f"v{v2} Property Checking Time [s]")
    axs[1].grid(True, which='major', ls='--')
    axs[1].legend()
    axs[1].set_title(f"Property Check | v{v2} better in {worse_v1_pc_count / len(all_v1_pt) * 100:.2f}%")

    # --- Statistic Info ---
    fig.text(0.5, 0.01, f"v{v1} TT: μ={mean_v1_tt:.5f}, σ={std_v1_tt:.5f} | v{v2} TT: μ={mean_v2_tt:.5f}, σ={std_v2_tt:.5f} || v{v1} PT: μ={mean_v1_pt:.5f}, σ={std_v1_pt:.5f} | v{v2} PT: μ={mean_v2_pt:.5f}, σ={std_v2_pt:.5f}", ha='center', fontsize=9)

    fig.tight_layout(rect=(0, 0.05, 1, 0.95))

    if save_plots:
        filename = f"{plot_name}_times_combined"
        if use_global_path:
            if os.path.exists(os.path.join(GLOBAL_IN_OUT_PATH, "benchmarks", filename + ".png")):
                i = 1
                while os.path.exists(os.path.join(GLOBAL_IN_OUT_PATH, "benchmarks", f"{filename}_{i} + .png")):
                    i += 1
                filename = os.path.join(GLOBAL_IN_OUT_PATH, "benchmarks", f"{filename}_{i}")
            else:
                filename = os.path.join(GLOBAL_IN_OUT_PATH, "benchmarks", filename)
        fig.savefig(filename + ".png")

    if not show_times:
        plt.close(fig)

    fig_stat, axs = plt.subplots(1, 2, figsize=(12, 6), num=plot_name + "_stats_comparison")
    fig_stat.suptitle("Combined Benchmark Graph Statistics (States vs. Transitions)")
    # Plot: Vertices

    axs[0].set_xscale('log')
    axs[0].set_yscale('log')
    for ssg_type in np.unique(ssg_type_array):
        mask = ssg_type_array == ssg_type
        axs[0].scatter(all_v1_v[mask], all_v2_v[mask], color=colors[ssg_type], label=labels[ssg_type])
    axs[0].plot(all_v1_v, all_v1_v, linestyle='-', color='black', label=f'#s with v{v1} = #s with v{v2}')
    axs[0].plot(all_v1_v, 2 * all_v1_v, linestyle='--', color='#808080')
    axs[0].plot(all_v1_v, 0.5 * all_v1_v, linestyle='--', color='#808080')
    axs[0].set_xlabel(f"v{v1} States")
    axs[0].set_ylabel(f"v{v2} States")
    axs[0].set_title(f"States | v{v2} less states than v{v1} in {worse_v1_v_count / len(all_v1_v) * 100:.2f}% of the cases")
    axs[0].legend()
    axs[0].grid(True, which='major', ls='--')

    # Plot: Transitions
    axs[1].set_xscale('log')
    axs[1].set_yscale('log')
    for ssg_type in np.unique(ssg_type_array):
        mask = ssg_type_array == ssg_type
        axs[1].scatter(all_v1_t[mask], all_v2_t[mask], color=colors[ssg_type], label=labels[ssg_type])
    axs[1].plot(all_v1_t, all_v1_t, linestyle='-', color='black', label=f'#t with v{v1} = #t with v{v2}')
    axs[1].plot(all_v1_t, 2 * all_v1_t, linestyle='--', color='#808080')
    axs[1].plot(all_v1_t, 0.5 * all_v1_t, linestyle='--', color='#808080')
    axs[1].set_xlabel(f"v{v1} Transitions")
    axs[1].set_ylabel(f"v{v2} Transitions")
    axs[1].set_title(f"Transitions | v{v2} less transitions than v{v1} in {worse_v1_t_count / len(all_v1_t) * 100:.2f}% of the cases")
    axs[1].legend()
    axs[1].grid(True, which='major', ls='--')

    # --- Statistic Info ---
    fig_stat.text(0.5, 0.01, f"v{v1} States: μ={mean_v1_v:.2f}, σ={std_v1_v:.2f} | v{v2} States: μ={mean_v2_v:.2f}, σ={std_v2_v:.2f} || v{v1} Transitions: μ={mean_v1_t:.2f}, σ={std_v1_t:.2f} | v{v2} Transitions: μ={mean_v2_t:.2f}, σ={std_v2_t:.2f}", ha='center', fontsize=9)

    fig_stat.tight_layout(rect=(0, 0.05, 1, 0.95))
    if save_plots:
        filename = f"{plot_name}_stats_combined"
        if use_global_path:
            if os.path.exists(os.path.join(GLOBAL_IN_OUT_PATH, "benchmarks", filename + ".png")):
                i = 1
                while os.path.exists(os.path.join(GLOBAL_IN_OUT_PATH, "benchmarks", f"{filename}_{i} + .png")):
                    i += 1
                filename = os.path.join(GLOBAL_IN_OUT_PATH, "benchmarks", f"{filename}_{i}")
            else:
                filename = os.path.join(GLOBAL_IN_OUT_PATH, "benchmarks", filename)
        fig_stat.savefig(filename + ".png")

    if not show_stats:
        plt.close(fig_stat)

    if show_times or show_stats:
        plt.show()


def main():
    """
    Adjustable main function that is executed when the script is run.
    """
    list_of_benchmark_results = [(benchmark_exponential_ssgs(ssg_type="random", time_per_iteration=1200, save_results=True, use_global_path=True, force=True, debug=True))]
    list_of_benchmark_results.append((benchmark_exponential_ssgs(ssg_type="random_no_additional_selfloops", time_per_iteration=1200, save_results=True, use_global_path=True, force=True, debug=True)))
    list_of_benchmark_results.append((benchmark_exponential_ssgs(ssg_type="binary", time_per_iteration=1200, save_results=True, use_global_path=True, force=True, debug=True)))
    list_of_benchmark_results.append((benchmark_exponential_ssgs(ssg_type="complete", time_per_iteration=1200, save_results=True, use_global_path=True, force=True, debug=True)))
    list_of_benchmark_results.append((benchmark_exponential_ssgs(ssg_type="chain", time_per_iteration=1200, save_results=True, use_global_path=True, force=True, debug=True)))
    list_of_benchmark_results.append((benchmark_exponential_ssgs(ssg_type="empty", time_per_iteration=1200, save_results=True, use_global_path=True, force=True, debug=True)))
    plot_combined_benchmark_results(list_of_benchmark_results, show_times=True, show_stats=True, plot_name="test_benchmark_exponential_combined", save_plots=True, use_global_path=True, versions=(1, 2))


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
