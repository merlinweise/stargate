import random
import matplotlib
import os
import time
import re
import contextlib
import io
from multiprocessing import Process, Queue
import queue as pyqueue  # to handle Empty exception
from ssg_to_smg import ssg_to_smgspec, save_smg_file, check_target_reachability
from simplestochasticgame import SsgVertex, SsgTransition, SimpleStochasticGame, is_deadlock_vertex
from error_handling import print_error, print_debug
from settings import GLOBAL_DEBUG, GLOBAL_IN_OUT_PATH
from shell_commands import run_command


def create_random_ssg(number_of_vertices: int, number_of_transitions: int, number_of_target_vertices: int, no_additional_selfloops: bool = False, debug: bool = GLOBAL_DEBUG) -> SimpleStochasticGame:
    """
    Create a new SSG with random parameters.
    :param number_of_vertices: Maximum number of vertices in the SSG
    :type number_of_vertices: int
    :param number_of_transitions: Maximum number of transitions in the SSG
    :type number_of_transitions: int
    :param number_of_target_vertices: Maximum number of target vertices in the SSG
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
    for start_vertex in vertices.values():
        type_of_transition = random.choice([0, 1])
        if type_of_transition == 0:
            end_vertex = random.choice(list(vertices.values()))
            transitions[(start_vertex, str(action))] = SsgTransition(start_vertex, {(1.0, end_vertex)}, str(action))
        else:
            end_vertices = random.sample(list(vertices.values()), 2)
            transitions[(start_vertex, str(action))] = SsgTransition(start_vertex, {(0.5, end_vertices[0]), (0.5, end_vertices[1])}, str(action))
        action += 1
    for i in range(number_of_transitions-number_of_vertices):
        start_vertex = random.choice(list(vertices.values()))
        type_of_transition = random.choice([0, 1])
        if type_of_transition == 0:
            end_vertex = random.choice(list(vertices.values()))
            transitions[(start_vertex, str(action))] = SsgTransition(start_vertex, {(1.0, end_vertex)}, str(action))
        else:
            end_vertices = random.sample(list(vertices.values()), 2)
            transitions[(start_vertex, str(action))] = SsgTransition(start_vertex, {(0.5, end_vertices[0]), (0.5, end_vertices[1])}, str(action))
        action += 1
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
                    transitions[(vertices[parent_vertex_name], "a")] = SsgTransition(vertices[parent_vertex_name], {(0.5, vertices[vertex_name]), (0.5, vertices[f"layer_{layer}_vertex_{i-1}"])}, "a")
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
            transitions[(vertices[f"vertex_{i-1}"], "a")] = SsgTransition(vertices[f"vertex_{i-1}"], {(0.5, vertices[vertex_name]), (0.5, vertices["vertex_0"])}, "a")
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


def check_smg_stats(smg_file: str, debug: bool = GLOBAL_DEBUG, use_global_path: bool = False) -> tuple[int, int, float]:
    """
    Check the statistics of an SMG file.
    :param smg_file: Path to the SMG file
    :type smg_file: str
    :param debug: Whether to print debug information
    :type debug: bool
    :param use_global_path: Whether to use the global path for the SMG file
    :type use_global_path: bool
    """
    if use_global_path:
        smg_file = os.path.join(GLOBAL_IN_OUT_PATH, smg_file)
    if not os.path.exists(smg_file):
        print_error(f"SMG file {smg_file} does not exist.")

    command = ["prism", smg_file, "-noprobchecks"]
    if debug:
        print_debug(f"Running command: {' '.join(command)}")
    result = run_command(command, use_shell=True)
    if result.returncode != 0:
        print_error(f"Error running command: {result.stderr}")
    output = result.stdout
    match = re.search(r'States:(\s|\t)*(\d+)', output)
    states = int(match.group(2)) if match else -1
    match = re.search(r'Transitions:(\s|\t)*(\d+)', output)
    transitions = int(match.group(2)) if match else -1
    match = re.search(r'Time for model construction:(\s|\t)*(\d+\.\d+)', output)
    constr_time = float(match.group(2)) if match else "-1"
    return states, transitions, constr_time


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


def benchmark_multiple_ssgs(ssg_count: int, ssg_type: str, size_param: int, write: bool = None, result_path: str = None, use_global_path: bool = False, force: bool = True, debug: bool = GLOBAL_DEBUG, print_result: bool = False) -> tuple[list[float], list[float], list[float], list[float], list[int], list[int], list[int], list[int], tuple[str, str, int, int]]:
    """
    Benchmark the creation and property checking of multiple SSGs.
    :param ssg_count: Number of SSGs to create
    :type ssg_count: int
    :param ssg_type: Type of SSG to create (random, binary, empty)
    :type ssg_type: str
    :param size_param: Size parameter for the SSG
    :type size_param: int
    :param write: Whether to write the benchmark results to a file
    :type write: bool
    :param result_path: Path to save the benchmark results
    :type result_path: str
    :param use_global_path: Whether to use the global path for the SMG file
    :type use_global_path: bool
    :param force: Whether to force the creation of the SSG
    :type force: bool
    :param debug: Whether to print debug information
    :type debug: bool
    :param print_result: Whether to print the result of the benchmark
    :type print_result: bool
    :return: Tuple containing the average transformation and property checking times for both versions
    :rtype: tuple[list[float], list[float], list[float], list[float], list[int], list[int], list[int], list[int], tuple[str, str, int, int]]
    """
    import time
    total_v1_trans_time = 0.0
    total_v2_trans_time = 0.0
    total_v1_prop_time = 0.0
    total_v2_prop_time = 0.0
    all_v1_trans_times = []
    all_v2_trans_times = []
    all_v1_prop_times = []
    all_v2_prop_times = []
    total_v1_vertices = 0
    total_v2_vertices = 0
    total_v1_transitions = 0
    total_v2_transitions = 0
    all_v1_vertices = []
    all_v2_vertices = []
    all_v1_transitions = []
    all_v2_transitions = []
    if result_path is None:
        result_path = f"benchmark_results_normal_{ssg_count}_{ssg_type}_{size_param}.txt"
    if use_global_path:
        result_path = os.path.join(GLOBAL_IN_OUT_PATH, result_path)
    if write is None:
        write = False if not force and os.path.exists(result_path) and os.path.getsize(result_path) > 0 else True
    output = ""
    if debug:
        match ssg_type:
            case "random":
                print_debug(f"Creating {ssg_count} random SSGs with {size_param} vertices and {5*size_param} transitions.")
            case "random_no_additional_selfloops":
                print_debug(f"Creating {ssg_count} random SSGs with {size_param} vertices and {5*size_param} transitions without additional self-loops.")
            case "binary":
                print_debug(f"Creating {ssg_count} binary tree SSGs with {size_param} layers and {round(0.3*(2**size_param)/2)} target vertices.")
            case "complete":
                print_debug(f"Creating {ssg_count} complete graph SSGs with {size_param} vertices and {max(1, size_param//10)} target vertices.")
            case "chain":
                print_debug(f"Creating {ssg_count} chain SSGs with {size_param} vertices.")
            case _:
                print_debug(f"Creating {ssg_count} empty SSGs with {size_param} vertices.")
    output += "Benchmark-Resultate\n"
    for i in range(ssg_count):
        if debug:
            print_debug(f"{i}/{ssg_count} SSGs created and evaluated.")
        if ssg_type == "random":
            ssg_i = create_random_ssg(size_param, 5*size_param, max(1, size_param//10), no_additional_selfloops=False)
        elif ssg_type == "random_no_additional_selfloops":
            ssg_i = create_random_ssg(size_param, 5*size_param, max(1, size_param//10), no_additional_selfloops=True)
        elif ssg_type == "binary":
            ssg_i = create_binary_tree_ssg(size_param, 0.3)
        elif ssg_type == "complete":
            ssg_i = create_complete_graph_ssg(size_param, max(1, size_param//10))
        elif ssg_type == "chain":
            ssg_i = create_chain_ssg(size_param)
        else:
            ssg_i = create_empty_ssg(size_param)

        start_v1 = time.perf_counter()
        smg_v1 = ssg_to_smgspec(ssg_i, version1=True)
        trans_v1_time = time.perf_counter() - start_v1
        save_smg_file(smg_v1, f"ssg_{i+1}_v1.smg", use_global_path=True, force=True)
        start_v1_prop = time.perf_counter()
        check_target_reachability(f"ssg_{i+1}_v1.smg", print_probabilities=False, use_global_path=True)
        prop_v1_time = time.perf_counter() - start_v1_prop
        vert_v1, trans_v1, build_time1 = check_smg_stats(f"ssg_{i + 1}_v1.smg", use_global_path=True)

        start_v2 = time.perf_counter()
        smg_v2 = ssg_to_smgspec(ssg_i, version1=False)
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

        total_v1_trans_time += trans_v1_time
        total_v2_trans_time += trans_v2_time
        total_v1_prop_time += prop_v1_time
        total_v2_prop_time += prop_v2_time
        total_v1_vertices += vert_v1
        total_v2_vertices += vert_v2
        total_v1_transitions += trans_v1
        total_v2_transitions += trans_v2

    if debug:
        print_debug(f"{ssg_count}/{ssg_count} SSGs created and evaluated.")
    avg_v1_trans = total_v1_trans_time / ssg_count
    avg_v2_trans = total_v2_trans_time / ssg_count
    avg_v1_prop = total_v1_prop_time / ssg_count
    avg_v2_prop = total_v2_prop_time / ssg_count

    if (avg_v1_trans + avg_v1_prop) < (avg_v2_trans + avg_v2_prop):
        output += f"Version1 is faster.\n\tTransformation Delta: {avg_v1_trans-avg_v2_trans:.4f}\n\tProperty Delta: {avg_v1_prop-avg_v2_prop:.4f}\n"
        if print_result:
            print(f"Version1 is faster.\n\tTransformation Delta: {avg_v1_trans-avg_v2_trans:.4f}\n\tProperty Delta: {avg_v1_prop-avg_v2_prop:.4f}\n")
        if write:
            with open(result_path, "w") as f:
                f.write(output)
    else:
        output += f"Version2 is faster.\n\tTransformation Delta: {avg_v2_trans-avg_v1_trans:.4f}\n\tProperty Delta: {avg_v2_prop-avg_v1_prop:.4f}\n"
        if print_result:
            print(f"Version2 is faster.\n\tTransformation Delta: {avg_v2_trans-avg_v1_trans:.4f}\n\tProperty Delta: {avg_v2_prop-avg_v1_prop:.4f}\n")
        if write:
            with open(result_path, "w") as f:
                f.write(output)

    return all_v1_trans_times, all_v2_trans_times, all_v1_prop_times, all_v2_prop_times, all_v1_vertices, all_v2_vertices, all_v1_transitions, all_v2_transitions, ("norm", ssg_type, ssg_count, size_param)


def _iteration_worker(q, ssg_type, i, debug, use_global_path):
    """
    Worker function to run a single benchmark iteration and return results via Queue.
    """
    try:
        result = single_iteration_for_exponential_benchmark(ssg_type, i, debug, use_global_path)
        q.put(result)
    except Exception as e:
        q.put(e)


def single_iteration_for_exponential_benchmark(ssg_type: str, i: int, debug: bool = GLOBAL_DEBUG, use_global_path: bool = True) -> tuple[float, float, float, float, int, int, int, int, str, str, int]:
    if ssg_type == "binary":
        size_param = i + 2
    else:
        size_param = (2 ** (i + 1))
    if ssg_type == "random":
        ssg_i = create_random_ssg(size_param, 5 * size_param, max(1, size_param // 10),
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
    smg_v1 = ssg_to_smgspec(ssg_i, version1=True)
    trans_v1_time = time.perf_counter() - start_v1
    save_smg_file(smg_v1, f"ssg_{i + 1}_v1.smg", use_global_path=use_global_path, force=True)
    start_v1_prop = time.perf_counter()
    check_target_reachability(f"ssg_{i + 1}_v1.smg", print_probabilities=False, use_global_path=use_global_path)
    prop_v1_time = time.perf_counter() - start_v1_prop
    vert_v1, trans_v1, build_time1 = check_smg_stats(f"ssg_{i + 1}_v1.smg", use_global_path=use_global_path)

    start_v2 = time.perf_counter()
    smg_v2 = ssg_to_smgspec(ssg_i, version1=False)
    trans_v2_time = time.perf_counter() - start_v2
    save_smg_file(smg_v2, f"ssg_{i + 1}_v2.smg", use_global_path=use_global_path, force=True)
    start_v2_prop = time.perf_counter()
    check_target_reachability(f"ssg_{i + 1}_v2.smg", print_probabilities=False, use_global_path=use_global_path)
    prop_v2_time = time.perf_counter() - start_v2_prop
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


def benchmark_exponential_ssgs(ssg_type: str, time_per_iteration: int = 600, write: bool = None, result_path: str = None, use_global_path: bool = True, force: bool = True, debug: bool = GLOBAL_DEBUG, print_result: bool = False) -> tuple[list[float], list[float], list[float], list[float], list[int], list[int], list[int], list[int], tuple[str, str, int, int]]:
    """
        Benchmark the creation and property checking of multiple SSGs.
        :param ssg_type: Type of SSG to create (random, binary, empty)
        :type ssg_type: str
        :param time_per_iteration: Time in seconds for each iteration
        :type time_per_iteration: int
        :param write: Whether to write the benchmark results to a file
        :type write: bool
        :param result_path: Path to save the benchmark results
        :type result_path: str
        :param use_global_path: Whether to use the global path for the SMG file
        :type use_global_path: bool
        :param force: Whether to force the creation of the SSG
        :type force: bool
        :param debug: Whether to print debug information
        :type debug: bool
        :param print_result: Whether to print the result of the benchmark
        :type print_result: bool
        :return: Tuple containing the average transformation and property checking times for both versions
        :rtype: tuple[list[float], list[float], list[float], list[float], list[int], list[int], list[int], list[int], tuple[str, str, int, int]]
        """

    total_v1_trans_time = 0.0
    total_v2_trans_time = 0.0
    total_v1_prop_time = 0.0
    total_v2_prop_time = 0.0
    all_v1_trans_times = []
    all_v2_trans_times = []
    all_v1_prop_times = []
    all_v2_prop_times = []
    total_v1_vertices = 0
    total_v2_vertices = 0
    total_v1_transitions = 0
    total_v2_transitions = 0
    all_v1_vertices = []
    all_v2_vertices = []
    all_v1_transitions = []
    all_v2_transitions = []
    if result_path is None:
        result_path = f"benchmark_results_exponential_{ssg_type}_max_{time_per_iteration}.txt"
    if use_global_path:
        result_path = os.path.join(GLOBAL_IN_OUT_PATH, result_path)
    if write is None:
        write = False if not force and os.path.exists(result_path) and os.path.getsize(result_path) > 0 else True
    output = ""
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
    output += "Benchmark-Resultate\n"
    i = 0
    while True:
        q = Queue()
        p = Process(target=_iteration_worker, args=(q, ssg_type, i, debug, use_global_path))
        start_time = time.perf_counter()
        p.start()
        p.join(timeout=time_per_iteration)
        end_time = time.perf_counter()

        if p.is_alive():
            if debug:
                print_debug(f"Timeout of {time_per_iteration} seconds reached for SSG {i + 1}.")
            p.terminate()
            p.join()
            for path in [f"ssg_{i + 1}_v1.smg", f"ssg_{i + 1}_v2.smg"]:
                try:
                    os.remove(os.path.join(GLOBAL_IN_OUT_PATH, path) if use_global_path else path)
                except FileNotFoundError:
                    pass
            break

        # Get result from the Queue
        try:
            result = q.get_nowait()
        except pyqueue.Empty:
            print_error(f"Error: No result received from subprocess for SSG {i + 1}.")
            break

        if isinstance(result, Exception):
            print_error(f"Subprocess failed with exception: {result}")
            break

        (trans_v1_time, trans_v2_time, prop_v1_time, prop_v2_time,
         vert_v1, vert_v2, trans_v1, trans_v2,
         smg_v1_path, smg_v2_path, size_param) = result

        if vert_v1 < 0 or vert_v2 < 0 or trans_v1 < 0 or trans_v2 < 0:
            print_error(f"Error: Negative values for vertices or transitions in SSG {i + 1}.")
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

        total_v1_trans_time += trans_v1_time
        total_v2_trans_time += trans_v2_time
        total_v1_prop_time += prop_v1_time
        total_v2_prop_time += prop_v2_time
        total_v1_vertices += vert_v1
        total_v2_vertices += vert_v2
        total_v1_transitions += trans_v1
        total_v2_transitions += trans_v2

        i += 1

    avg_v1_trans = total_v1_trans_time / max(len(all_v1_trans_times), 1)
    avg_v2_trans = total_v2_trans_time / max(len(all_v2_trans_times), 1)
    avg_v1_prop = total_v1_prop_time / max(len(all_v1_prop_times), 1)
    avg_v2_prop = total_v2_prop_time / max(len(all_v2_prop_times), 1)

    if (avg_v1_trans + avg_v1_prop) < (avg_v2_trans + avg_v2_prop):
        output += f"Version1 is faster.\n\tTransformation Delta: {avg_v1_trans - avg_v2_trans:.4f}\n\tProperty Delta: {avg_v1_prop - avg_v2_prop:.4f}\n"
        if print_result:
            print(
                f"Version1 is faster.\n\tTransformation Delta: {avg_v1_trans - avg_v2_trans:.4f}\n\tProperty Delta: {avg_v1_prop - avg_v2_prop:.4f}\n")
        if write:
            with open(result_path, "w") as f:
                f.write(output)
    else:
        output += f"Version2 is faster.\n\tTransformation Delta: {avg_v2_trans - avg_v1_trans:.4f}\n\tProperty Delta: {avg_v2_prop - avg_v1_prop:.4f}\n"
        if print_result:
            print(
                f"Version2 is faster.\n\tTransformation Delta: {avg_v2_trans - avg_v1_trans:.4f}\n\tProperty Delta: {avg_v2_prop - avg_v1_prop:.4f}\n")
        if write:
            with open(result_path, "w") as f:
                f.write(output)

    return all_v1_trans_times, all_v2_trans_times, all_v1_prop_times, all_v2_prop_times, all_v1_vertices, all_v2_vertices, all_v1_transitions, all_v2_transitions, ("ex", ssg_type, size_param, time_per_iteration)


def plot_benchmark_results(all_v1_trans_times: list[float], all_v2_trans_times: list[float], all_v1_prop_times: list[float], all_v2_prop_times: list[float], all_v1_vertices: list[int], all_v2_vertices: list[int], all_v1_transitions: list[int], all_v2_transitions: list[int], benchmark_info: tuple[str, str, int, int], show_times: bool = True, show_stats: bool = True, plot_name: str = None, save_plots: bool = False, use_global_path: bool = True, debug: bool = GLOBAL_DEBUG) -> None:
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
    :param debug: Whether to print debug information
    :type debug: bool
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
    axs[0].scatter(x1[mask_below1], y1[mask_below1], color='blue', label='v2 faster than v1')
    axs[0].scatter(x1[mask_above1], y1[mask_above1], color='red', label='v1 faster than v2')
    axs[0].plot(x1, x1, linestyle='-', color='gray', label='v1 and v2 equal')
    axs[0].set_xlabel("v1 Transformation Time [s]")
    axs[0].set_ylabel("v2 Transformation Time [s]")
    axs[0].grid(True, which='major', ls='--')
    axs[0].legend()
    axs[0].set_title(f"Transformation | v1 better in {better_v1_tt_count / len(x1) * 100:.2f}%")

    # --- Plot 2: Property Checking Time ---
    axs[1].set_xscale('log')
    axs[1].set_yscale('log')
    axs[1].scatter(x2[mask_below2], y2[mask_below2], color='blue', label='v2 faster than v1')
    axs[1].scatter(x2[mask_above2], y2[mask_above2], color='red', label='v1 faster than v2')
    axs[1].plot(x2, x2, linestyle='-', color='gray', label='v1 and v2 equal')
    axs[1].set_xlabel("v1 Property Checking Time [s]")
    axs[1].set_ylabel("v2 Property Checking Time [s]")
    axs[1].grid(True, which='major', ls='--')
    axs[1].legend()
    axs[1].set_title(f"Property Check | v1 better in {better_v1_pc_count / len(x2) * 100:.2f}%")

    # --- Gemeinsame Statistik-Info ---
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
    axs[0].scatter(x3[mask_below3], y3[mask_below3], color='blue', label='#v with v2 < #v with v1')
    axs[0].scatter(x3[mask_above3], y3[mask_above3], color='red', label='#v with v1 < #v with v2')
    axs[0].plot(x3, x3, linestyle='-', color='gray', label='#v with v1 = #v with v2')
    axs[0].set_xlabel("v1 Vertices")
    axs[0].set_ylabel("v2 Vertices")
    axs[0].set_title(f"Vertices | v1 less vertices than v2 in {better_v1_v_count / len(x3) * 100:.2f}% of the cases")
    axs[0].legend()
    axs[0].grid(True, which='major', ls='--')

    # Plot: Transitions
    axs[1].set_xscale('log')
    axs[1].set_yscale('log')
    axs[1].scatter(x4[mask_below4], y4[mask_below4], color='blue', label='#t with v2 < #t with v1')
    axs[1].scatter(x4[mask_above4], y4[mask_above4], color='red', label='#t with v1 < #t with v2')
    axs[1].plot(x4, x4, linestyle='-', color='gray', label='#t with v1 = #t with v2')
    axs[1].set_xlabel("v1 Transitions")
    axs[1].set_ylabel("v2 Transitions")
    axs[1].set_title(f"Transitions | v1 less transitions than v2 in {better_v1_t_count / len(x4) * 100:.2f}% of the cases")
    axs[1].legend()
    axs[1].grid(True, which='major', ls='--')

    fig_stat.text(0.5, 0.01,
                  f"v1 Vertices: μ={mean_v1_v:.2f}, σ={std_v1_v:.2f} | "
                  f"v2 Vertices: μ={mean_v2_v:.2f}, σ={std_v2_v:.2f}",
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


#p1, p2, p3, p4, p5, p6, p7, p8, info = benchmark_multiple_ssgs(100, "random", size_param=500, use_global_path=True, debug=True, force=True, print_result=False, write=False)
#plot_benchmark_results(p1, p2, p3, p4, p5, p6, p7, p8, benchmark_info=info, use_global_path=True, save_plots=True, show_times=False, show_stats=False)
#p1, p2, p3, p4, p5, p6, p7, p8, info = benchmark_multiple_ssgs(100, "random_no_additional_selfloops", size_param=500, use_global_path=True, debug=True, force=True, print_result=False, write=False)
#plot_benchmark_results(p1, p2, p3, p4, p5, p6, p7, p8, benchmark_info=info, use_global_path=True, save_plots=True, show_times=False, show_stats=False)
#p1, p2, p3, p4, p5, p6, p7, p8, info = benchmark_multiple_ssgs(100, "binary", size_param=9, use_global_path=True, debug=True, force=True, print_result=False, write=False)
#plot_benchmark_results(p1, p2, p3, p4, p5, p6, p7, p8, benchmark_info=info, use_global_path=True, save_plots=True, show_times=False, show_stats=False)
#p1, p2, p3, p4, p5, p6, p7, p8, info = benchmark_multiple_ssgs(100, "complete", size_param=100, use_global_path=True, debug=True, force=True, print_result=False, write=False)
#plot_benchmark_results(p1, p2, p3, p4, p5, p6, p7, p8, benchmark_info=info, use_global_path=True, save_plots=True, show_times=False, show_stats=False)
#p1, p2, p3, p4, p5, p6, p7, p8, info = benchmark_multiple_ssgs(100, "chain", size_param=500, use_global_path=True, debug=True, force=True, print_result=False, write=False)
#plot_benchmark_results(p1, p2, p3, p4, p5, p6, p7, p8, benchmark_info=info, use_global_path=True, save_plots=True, show_times=False, show_stats=False)
#p1, p2, p3, p4, p5, p6, p7, p8, info = benchmark_multiple_ssgs(100, "empty", size_param=500, use_global_path=True, debug=True, force=True, print_result=False, write=False)
#plot_benchmark_results(p1, p2, p3, p4, p5, p6, p7, p8, benchmark_info=info, use_global_path=True, save_plots=True, show_times=False, show_stats=False)


def main():
    p1, p2, p3, p4, p5, p6, p7, p8, info = benchmark_exponential_ssgs(
        "random",
        time_per_iteration=1800,
        use_global_path=True,
        debug=True,
        force=True,
        print_result=False,
        write=False
    )
    plot_benchmark_results(
        p1, p2, p3, p4, p5, p6, p7, p8,
        benchmark_info=info,
        use_global_path=True,
        save_plots=True,
        show_times=False,
        show_stats=False
    )
    p1, p2, p3, p4, p5, p6, p7, p8, info = benchmark_exponential_ssgs(
        "random_no_additional_selfloops",
        time_per_iteration=1800,
        use_global_path=True,
        debug=True,
        force=True,
        print_result=False,
        write=False
    )
    plot_benchmark_results(
        p1, p2, p3, p4, p5, p6, p7, p8,
        benchmark_info=info,
        use_global_path=True,
        save_plots=True,
        show_times=False,
        show_stats=False
    )
    p1, p2, p3, p4, p5, p6, p7, p8, info = benchmark_exponential_ssgs(
        "binary",
        time_per_iteration=1800,
        use_global_path=True,
        debug=True,
        force=True,
        print_result=False,
        write=False
    )
    plot_benchmark_results(
        p1, p2, p3, p4, p5, p6, p7, p8,
        benchmark_info=info,
        use_global_path=True,
        save_plots=True,
        show_times=False,
        show_stats=False
    )
    p1, p2, p3, p4, p5, p6, p7, p8, info = benchmark_exponential_ssgs(
        "complete",
        time_per_iteration=1800,
        use_global_path=True,
        debug=True,
        force=True,
        print_result=False,
        write=False
    )
    plot_benchmark_results(
        p1, p2, p3, p4, p5, p6, p7, p8,
        benchmark_info=info,
        use_global_path=True,
        save_plots=True,
        show_times=False,
        show_stats=False
    )
    p1, p2, p3, p4, p5, p6, p7, p8, info = benchmark_exponential_ssgs(
        "chain",
        time_per_iteration=1800,
        use_global_path=True,
        debug=True,
        force=True,
        print_result=False,
        write=False
    )
    plot_benchmark_results(
        p1, p2, p3, p4, p5, p6, p7, p8,
        benchmark_info=info,
        use_global_path=True,
        save_plots=True,
        show_times=False,
        show_stats=False
    )
    p1, p2, p3, p4, p5, p6, p7, p8, info = benchmark_exponential_ssgs(
        "empty",
        time_per_iteration=1800,
        use_global_path=True,
        debug=True,
        force=True,
        print_result=False,
        write=False
    )
    plot_benchmark_results(
        p1, p2, p3, p4, p5, p6, p7, p8,
        benchmark_info=info,
        use_global_path=True,
        save_plots=True,
        show_times=False,
        show_stats=False
    )


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()  # Optional, hilft bei frozen executables
    main()
