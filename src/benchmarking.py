import random
from ssg_to_smg import *
from error_handling import print_error, print_debug


def create_random_ssg(number_of_vertices: int, number_of_transitions: int, number_of_target_vertices: int, debug: bool = GLOBAL_DEBUG) -> SimpleStochasticGame:
    """
    Create a new SSG with random parameters.
    :param number_of_vertices: Maximum number of vertices in the SSG
    :type number_of_vertices: int
    :param number_of_transitions: Maximum number of transitions in the SSG
    :type number_of_transitions: int
    :param number_of_target_vertices: Maximum number of target vertices in the SSG
    :type number_of_target_vertices: int
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
        smg_file = os.path.join(global_in_out_path, smg_file)
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


ssg = create_empty_ssg(100000)
smg = ssg_to_smgspec(ssg, version1=True)
save_smg_file(smg, "empty_100000.smg", use_global_path=True, force=True)
print_smg_stats("empty_100000.smg",  use_global_path=True)
check_target_reachability("empty_10000.smg", print_probabilities=True, use_global_path=True)
create_dot_file("empty_100000.smg", use_global_path=True, force=True)
create_png_file("empty_100000.dot", use_global_path=True, force=True, open_png=True)
