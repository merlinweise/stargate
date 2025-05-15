import random
from ssg_to_smg import *
from simplestochasticgame import is_deadlock_vertex
from error_handling import print_error, print_debug


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
        transitions[(vertices[vertex_name], "a")] = SsgTransition(vertices[vertex_name], {(1.0/number_of_vertices, vertices[end_vertex_name]) for end_vertex_name in vertices}, "a")
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


def benchmark_multiple_ssgs(ssg_count: int, ssg_type: str, size_param: int, result_path: str = None, use_global_path: bool = False, force: bool = True, debug: bool = GLOBAL_DEBUG, print_result: bool = False) -> bool:
    """
    Benchmark the creation and property checking of multiple SSGs.
    :param ssg_count: Number of SSGs to create
    :type ssg_count: int
    :param ssg_type: Type of SSG to create (random, binary, empty)
    :type ssg_type: str
    :param size_param: Size parameter for the SSG
    :type size_param: int
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
    """
    import time
    total_v1_trans_time = 0.0
    total_v2_trans_time = 0.0
    total_v1_prop_time = 0.0
    total_v2_prop_time = 0.0
    if result_path is None:
        result_path = f"benchmark_results_{ssg_count}_{ssg_type}_{size_param}.txt"
    if use_global_path:
        result_path = os.path.join(GLOBAL_IN_OUT_PATH, result_path)
    write = False if not force and os.path.exists(result_path) and os.path.getsize(result_path) > 0 else True
    output = ""
    if debug:
        match ssg_type:
            case "random":
                print_debug(f"Creating {ssg_count} random SSGs with {size_param} vertices and transitions.")
            case "binary":
                print_debug(f"Creating {ssg_count} binary tree SSGs with {size_param} layers and {0.3*size_param/2} target vertices.")
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
            ssg_i = create_random_ssg(size_param, size_param, max(1, size_param//10), no_additional_selfloops=False)
        elif ssg_type == "random_no_additional_selfloops":
            ssg_i = create_random_ssg(size_param, size_param, max(1, size_param//10), no_additional_selfloops=True)
        elif ssg_type == "binary":
            ssg_i = create_binary_tree_ssg(size_param, 0.3)
        elif ssg_type == "complete":
            ssg_i = create_complete_graph_ssg(size_param, max(1, size_param//10))
        elif ssg_type == "chain":
            ssg_i = create_chain_ssg(size_param)
        else:
            ssg_i = create_empty_ssg(size_param)

        start_v1 = time.time()
        smg_v1 = ssg_to_smgspec(ssg_i, version1=True)
        trans_v1_time = time.time() - start_v1
        save_smg_file(smg_v1, f"ssg_{i+1}_v1.smg", use_global_path=True, force=True)
        start_v1_prop = time.time()
        check_target_reachability(f"ssg_{i+1}_v1.smg", print_probabilities=False, use_global_path=True)
        prop_v1_time = time.time() - start_v1_prop

        start_v2 = time.time()
        smg_v2 = ssg_to_smgspec(ssg_i, version1=False)
        trans_v2_time = time.time() - start_v2
        save_smg_file(smg_v2, f"ssg_{i+1}_v2.smg", use_global_path=True, force=True)
        start_v2_prop = time.time()
        check_target_reachability(f"ssg_{i+1}_v2.smg", print_probabilities=False, use_global_path=True)
        prop_v2_time = time.time() - start_v2_prop
        if use_global_path:
            smg_v1_path = os.path.join(GLOBAL_IN_OUT_PATH, f"ssg_{i+1}_v1.smg")
            smg_v2_path = os.path.join(GLOBAL_IN_OUT_PATH, f"ssg_{i+1}_v2.smg")
        os.remove(smg_v1_path)
        os.remove(smg_v2_path)

        total_v1_trans_time += trans_v1_time
        total_v2_trans_time += trans_v2_time
        total_v1_prop_time += prop_v1_time
        total_v2_prop_time += prop_v2_time

        output += f"SSG {i+1} transforming time :\n\tv1={trans_v1_time:.4f}\n\tv2={trans_v2_time:.4f}\n"
        output += f"SSG {i+1} property checking time :\n\tv1={prop_v1_time:.4f}\n\tv2={prop_v2_time:.4f}\n"

    avg_v1_trans = total_v1_trans_time / ssg_count
    avg_v2_trans = total_v2_trans_time / ssg_count
    avg_v1_prop = total_v1_prop_time / ssg_count
    avg_v2_prop = total_v2_prop_time / ssg_count
    output += (
        f"\nAverage Times:\n"
        f"\tVersion1 - Transformation: {avg_v1_trans:.4f} Property: {avg_v1_prop:.4f}\n"
        f"\tVersion2 - Transformation: {avg_v2_trans:.4f} Property: {avg_v2_prop:.4f}\n"
    )

    if (avg_v1_trans + avg_v1_prop) < (avg_v2_trans + avg_v2_prop):
        output += f"Version1 is faster.\n\tTransformation Delta: {avg_v1_trans-avg_v2_trans:.4f}\n\tProperty Delta: {avg_v1_prop-avg_v2_prop:.4f}\n"
        if print_result:
            print(f"Version1 is faster.\n\tTransformation Delta: {avg_v1_trans-avg_v2_trans:.4f}\n\tProperty Delta: {avg_v1_prop-avg_v2_prop:.4f}\n")
        if write:
            with open(result_path, "w") as f:
                f.write(output)
        return True
    else:
        output += f"Version2 is faster.\n\tTransformation Delta: {avg_v2_trans-avg_v1_trans:.4f}\n\tProperty Delta: {avg_v2_prop-avg_v1_prop:.4f}\n"
        if print_result:
            print(f"Version2 is faster.\n\tTransformation Delta: {avg_v2_trans-avg_v1_trans:.4f}\n\tProperty Delta: {avg_v2_prop-avg_v1_prop:.4f}\n")
        if write:
            with open(result_path, "w") as f:
                f.write(output)
        return False


benchmark_multiple_ssgs(
    ssg_count=500,
    ssg_type="random",
    size_param=10,
    use_global_path=True,
    debug=True,
    force=True,
    print_result=True
)
benchmark_multiple_ssgs(
    ssg_count=500,
    ssg_type="random_no_additional_selfloops",
    size_param=10,
    use_global_path=True,
    debug=True,
    force=True,
    print_result=True
)
