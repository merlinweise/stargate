import re
import os
import time
from fractions import Fraction

from settings import GLOBAL_DEBUG, GLOBAL_IN_OUT_PATH_WINDOWS, PRINT_VERTEX_CREATION_WARNINGS, GLOBAL_IN_OUT_PATH, USE_EXACT_ARITHMETIC, MAX_DENOMINATOR
from error_handling import print_warning, print_error, print_debug, is_float_expr, float_or_fraction


class SpgVertex:

    def __init__(self, name: str, is_eve: bool, priority: int):
        """
        Creates a vertex of a stochastic parity game.
        :param name: Name of the vertex
        :type name: str
        :param is_eve: True if the vertex is controlled by Eve, False if it is controlled by Adam
        :type is_eve: bool
        :param priority: Value of the priority of the vertex
        :type priority: int
        """
        self.name = name
        self.is_eve = is_eve
        if priority < 0:
            print_error(f"Priority {priority} of vertex {name} is negative. This is not allowed.")
        self.priority = priority

    def __str__(self):
        """
        Returns a string representation of the vertex.
        :return: String representation of the vertex
        :rtype: str
        """
        if self.is_eve:
            return f"( {self.name} | E | {self.priority} )"
        else:
            return f"( {self.name} | A | {self.priority} )"


class SpgTransition:
    def __init__(self, start_vertex: SpgVertex, end_vertices: set[tuple[float, SpgVertex]], action: str):
        """
        Creates a transition of a stochastic parity game.
        :param start_vertex: Starting vertex of the transition
        :type start_vertex: SpgVertex
        :param end_vertices: Set of tuples of probabilities and respective end vertices
        :type end_vertices: set[(float, SpgVertex)]
        :param action: String representation of the action
        :type action: str
        """
        self.start_vertex = start_vertex
        self.end_vertices = end_vertices
        self.action = action
        total_prob = 0
        neg_probs = False
        for prob, vert in self.end_vertices:
            if prob < 0:
                neg_probs = True
            total_prob += prob
        if total_prob != 1:
            print_warning(f"Sum ({total_prob}) of probabilities does not equal 1 of edge from {self.start_vertex.name} with action {self.action}")
        if neg_probs:
            print_warning("There is at least one probability that is negative of edge from {self.start_vertex.name} with action {self.action}")
        if USE_EXACT_ARITHMETIC:
            # Change all probabilities to fractions
            self.end_vertices = set()
            for prob, vert in end_vertices:
                self.end_vertices.add((Fraction(prob).limit_denominator(MAX_DENOMINATOR), vert))

    def __str__(self):
        """
        Returns a string representation of the transition.
        :return: String representation of the transition
        :rtype: str
        """
        output = f"{self.start_vertex.name} | {self.action} | ( "

        for prob, vert in self.end_vertices:
            output += f"{prob} : {vert.name} + "
        output = output[:-2] + ")"
        return output


class StochasticParityGame:
    def __init__(self, vertices: dict[str, SpgVertex], transitions: dict[tuple[SpgVertex, str], SpgTransition], init_vertex: SpgVertex):
        """
        Creates a stochastic parity game and checks for deadlock vertices and vertices without ingoing transitions.
        :param vertices: Vertices of the stochastic parity game
        :type vertices: dict[str, SpgVertex]
        :param transitions: Transitions of the stochastic parity game
        :type transitions: dict[(SpgVertex, str), SpgTransition]
        :param init_vertex: Initial vertex of the stochastic parity game
        :type init_vertex: SpgVertex
        """
        self.vertices = vertices
        self.transitions = transitions
        self.init_vertex = init_vertex

        for vertex in self.vertices.values():
            if GLOBAL_DEBUG and PRINT_VERTEX_CREATION_WARNINGS and has_ingoing_transition(vertex, self.transitions):
                print_debug(f"Vertex {vertex.name} has no ingoing transition.")
            if is_deadlock_vertex(vertex, self.transitions):
                self.transitions[vertex, "selfloop"] = SpgTransition(vertex, {(1.0, vertex)}, "selfloop")
                if GLOBAL_DEBUG and PRINT_VERTEX_CREATION_WARNINGS:
                    print_debug(f"Vertex {vertex.name} is a deadlock vertex. A selfloop was added.")
        for vertex_name in vertices:
            if vertex_name != vertices[vertex_name].name:
                print_error(f"Key {vertex_name} in vertices dictionary does not match vertex name {vertices[vertex_name].name}. This is needed for the SPG to work correctly.")
        for transition_key in transitions:
            if transition_key[0] is not transitions[transition_key].start_vertex:
                print_error(f"Key {transition_key[0]} in transitions dictionary does not match transition start vertex {transitions[transition_key].start_vertex}. This is needed for the SPG to work correctly.")
            if transition_key[1] != transitions[transition_key].action:
                print_error(f"Key {transition_key[1]} in transitions dictionary does not match transition action {transitions[transition_key].action}. This is needed for the SPG to work correctly.")


def has_ingoing_transition(vertex: SpgVertex, transitions: dict[tuple[SpgVertex, str], SpgTransition]) -> bool:
    """
    Checks if the given vertex has an ingoing transition.
    :param vertex: Vertex to check
    :type vertex: SpgVertex
    :param transitions: Transitions of the stochastic parity game
    :type transitions: dict[(SpgVertex, str), SpgTransition]
    :return: True if the vertex has an ingoing transition, False otherwise
    :rtype: bool
    """
    for transition in transitions.values():
        for end_vertex in transition.end_vertices:
            if end_vertex[1] == vertex:
                return True
    return False


def is_deadlock_vertex(vertex: SpgVertex, transitions: dict[tuple[SpgVertex, str], SpgTransition]) -> bool:
    """
    Checks if a vertex is a deadlock vertex.
    :param vertex: Vertex to check
    :type vertex: SpgVertex
    :param transitions: Transitions of the stochastic parity game
    :type transitions: dict[(SpgVertex, str), SpgTransition]
    :return: True if the vertex is a deadlock vertex, False otherwise
    :rtype: bool
    """
    for transition in transitions.values():
        if transition.start_vertex == vertex:
            return False
    return True


def read_spg_from_file(file_name: str, use_global_path: bool = False, debug: bool = GLOBAL_DEBUG) -> StochasticParityGame:
    """
    Reads a stochastic parity game from a file and returns the corresponding StochasticParityGame object.
    :param file_name: Path to the file that is joined with the global_in_out_path
    :type file_name: str
    :param use_global_path: If True, the file_name is joined with the global_in_out_path
    :type use_global_path: bool
    :param debug: True if debug information should be printed
    :type debug: bool
    :return: StochasticParityGame object
    :rtype: StochasticParityGame
    """
    if debug:
        start_time = time.perf_counter()
    if use_global_path:
        file_name = os.path.join(GLOBAL_IN_OUT_PATH, file_name)
    if file_name[-4:] != ".spg":
        print_error("Not a .spg file")
    try:
        with open(file_name, "r") as file:
            content = file.readlines()
    except FileNotFoundError:
        print_error(f"File '{file_name}' not found.")
    except Exception as e:
        print_error(f"Could not read the file: {e}")

    if content[0] != "spg\n":
        print_error("Not an spg specification.")

    state = 0
    spg_vertices = dict()
    spg_initial_vertex = None
    spg_transitions = dict()
    for current_line_index in range(1, len(content)):
        current_line = re.split(r"\s+", content[current_line_index].replace("\t", " ").replace("\n", " ").replace(":", " : ").replace("|", " | ").replace("+", " + ").strip())
        match state:
            case 0:
                if current_line == [""]:
                    continue
                if current_line == ["evevertices"]:
                    state = 1
                    continue
                print_error(
                    f"File does not comply with spg specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 1:
                if current_line == [""]:
                    continue
                if current_line == ["endevevertices"]:
                    state = 2
                    continue
                if current_line[1] == ":" and current_line[2].isdigit() and int(current_line[2]) >= 0 and len(
                        current_line) == 3:
                    if current_line[0] in spg_vertices:
                        print_error(f"Duplicate vertex {current_line[0]}")
                    spg_vertices[current_line[0]] = SpgVertex(current_line[0], True, int(current_line[2]))
                    # print(spg_vertices[current_line[0]])
                    continue
                print_error(
                    f"File does not comply with spg specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 2:
                if current_line == [""]:
                    continue
                if current_line == ["adamvertices"]:
                    state = 3
                    continue
                print_error(
                    f"File does not comply with spg specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 3:
                if current_line == [""]:
                    continue
                if current_line == ["endadamvertices"]:
                    state = 4
                    continue
                if current_line[1] == ":" and current_line[2].isdigit() and int(current_line[2]) >= 0 and len(
                        current_line) == 3:
                    if current_line[0] in spg_vertices:
                        print_error(f"Duplicate vertex {current_line[0]}")
                    spg_vertices[current_line[0]] = SpgVertex(current_line[0], False, int(current_line[2]))
                    # print(spg_vertices[current_line[0]])
                    continue
                print_error(
                    f"File does not comply with spg specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 4:
                if current_line == [""]:
                    continue
                if len(current_line) == 3 and current_line[0] == "initialvertex" and current_line[1] == ":":
                    if current_line[2] not in spg_vertices:
                        print_error(f"Initial vertex {current_line[2]} was not declared before")
                    spg_initial_vertex = spg_vertices[current_line[2]]
                    # print(spg_inital_vertex)
                    state = 5
                    continue
                print_error(
                    f"File does not comply with spg specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 5:
                if current_line == [""]:
                    continue
                if current_line == ["transitions"]:
                    state = 6
                    continue
                print_error(
                    f"File does not comply with spg specification. Line {current_line_index + 1}: {content[current_line_index]}")
            case 6:
                if current_line == [""]:
                    continue
                if current_line == ["endtransitions"]:
                    break
                if len(current_line) == 4 and current_line[2] == ":":
                    if not (current_line[0] in spg_vertices):
                        print_error(
                            f"{current_line[0]} from transition {content[current_line_index]} was not specified as a vertex")
                    if not (current_line[3] in spg_vertices):
                        print_error(
                            f"{current_line[2]} from transition {content[current_line_index]} was not specified as a vertex")
                    if (spg_vertices[current_line[0]], current_line[1]) in spg_transitions:
                        print_error(
                            f"Duplicate transition from {spg_vertices[current_line[0]]} with action {current_line[1]}")
                    spg_transitions[(spg_vertices[current_line[0]], current_line[1])] = SpgTransition(
                        spg_vertices[current_line[0]], {(1.0, spg_vertices[current_line[3]])}, current_line[1])
                    continue
                if len(current_line) >= 6 and len(current_line) % 4 == 2:
                    if not (current_line[0] in spg_vertices):
                        print_error(
                            f"{current_line[0]} from transition {content[current_line_index]} was not specified as a vertex")
                    if current_line[2] != ":":
                        print_error(f"Expected \":\" in transition {content[current_line_index]}")
                    for i in range(3, len(current_line)):
                        if i % 4 == 3:
                            if not (is_float_expr(current_line[i])):
                                print_error(f"Expected float in transition {content[current_line_index]}")
                        elif i % 4 == 0:
                            if current_line[i] != "|":
                                print_error(f"Expected \"|\" in transition {content[current_line_index]}")
                        elif i % 4 == 1:
                            if not (current_line[i] in spg_vertices):
                                print_error(
                                    f"{current_line[i]} from transition {content[current_line_index]} was not specified as a vertex")
                        elif i % 4 == 2:
                            if current_line[i] != "+":
                                print_error(f"Expected \"+\" in transition {content[current_line_index]}")
                    if (spg_vertices[current_line[0]], current_line[1]) in spg_transitions:
                        print_error(
                            f"Duplicate transition from {spg_vertices[current_line[0]]} with action {current_line[1]}")
                    end_vertices = set()
                    for i in range(0, int((len(current_line) - 2) / 4)):
                        end_vertices.add((float(eval(current_line[3 + i * 4])), spg_vertices[current_line[5 + i * 4]]))
                    spg_transitions[(spg_vertices[current_line[0]], current_line[1])] = SpgTransition(
                        spg_vertices[current_line[0]], end_vertices, current_line[1])
                    continue
                print_error(
                    f"File does not comply with spg specification. Line {current_line_index + 1}: {content[current_line_index]}")
            case _:
                print_error("Undefined state")
    if debug:
        print_debug(f"SPG file {file_name} read in {(time.perf_counter() - start_time):.6f} seconds")
    return StochasticParityGame(spg_vertices, spg_transitions, spg_initial_vertex)


def spg_to_spgspec(spg: StochasticParityGame, debug: bool = GLOBAL_DEBUG) -> str:
    """
    Converts a StochasticParityGame object to a string representation in the spg specification format.
    :param spg: The StochasticParityGame object to convert
    :type spg: StochasticParityGame
    :param debug: True if debug information should be printed
    :type debug: bool
    :return: SPG specification string
    :rtype: str
    """
    if debug:
        start_time = time.perf_counter()
    content = "spg\n\n"
    eve_vertices = "evevertices\n"
    adam_vertices = "adamvertices\n"
    for vertex in spg.vertices.values():
        if vertex.is_eve:
            eve_vertices += f"\t{vertex.name} : {vertex.priority}\n"
        else:
            adam_vertices += f"\t{vertex.name} : {vertex.priority}\n"
    eve_vertices += "endevevertices\n\n"
    adam_vertices += "endadamvertices\n\n"
    content += eve_vertices + adam_vertices
    content += f"initialvertex : {spg.init_vertex.name}\n\n"
    content += "transitions\n"
    for vert_act, trans in spg.transitions.items():
        if len(trans.end_vertices) == 1:
            content += f"\t{vert_act[0].name} {vert_act[1]} : {next(iter(trans.end_vertices))[1].name}\n"
        else:
            transition_str = f"\t{vert_act[0].name} {vert_act[1]} : "
            for end_vert in trans.end_vertices:
                transition_str += f"{float_or_fraction(end_vert[0], 100000)} | {end_vert[1].name} + "
            transition_str = transition_str[:-3] + "\n"
            content += transition_str
    content += "endtransitions"
    if debug:
        print_debug(f"SPG specification created in {(time.perf_counter() - start_time):.6f} seconds")
    return content


def save_spg_file(spg_spec: str, file_name: str = "", use_global_path: bool = False, force: bool = False, debug: bool = GLOBAL_DEBUG):
    """
    Saves the given content to a file with the given name. If the file already exists and force is not set to True, nothing is changed.
    :param spg_spec: SPG specification to save
    :type spg_spec: str
    :param file_name: Name of the file to save the SPG specification to
    :type file_name: str
    :param use_global_path: True if the file_name should be joined with the global_in_out_path
    :type use_global_path: bool
    :param force: True if the file should be overwritten if it already exists
    :type force: bool
    :param debug: True if debug information should be printed
    :type debug: bool
    """
    if debug:
        start_time = time.perf_counter()
    if not file_name:
        file_name = "out.spg"
    if use_global_path:
        file_name = os.path.join(GLOBAL_IN_OUT_PATH, file_name)
    if not file_name.endswith(".spg"):
        print_warning(f"File {file_name} is not an .spg file. Nothing was changed")
    elif not force and os.path.exists(file_name) and os.path.getsize(file_name) != 0:
        print_warning(f"File {file_name} already exists. Nothing was changed")
    else:
        with open(file_name, "w") as file:
            file.write(spg_spec)
            if debug:
                print_debug(f"SPG file {file_name} saved successfully")

    if debug:
        print_debug(f"SPG file {file_name} created in {(time.perf_counter() - start_time):.6f} seconds")


def reformat_spgspec(file_name: str, use_global_path: bool = False, debug: bool = GLOBAL_DEBUG):
    """
    Reformats the given SPG specification file to the default format.
    :param file_name: Name of the file to reformat
    :type file_name: str
    :param use_global_path: True if the file_name should be joined with the global_in_out_path
    :type use_global_path: bool
    :param debug: True if debug information should be printed
    :type debug: bool
    """
    if debug:
        start_time = time.perf_counter()
    if use_global_path:
        file_name = os.path.join(GLOBAL_IN_OUT_PATH_WINDOWS, file_name)
    spg = read_spg_from_file(file_name=file_name, use_global_path=use_global_path, debug=False)
    content = spg_to_spgspec(spg)
    save_spg_file(spg_spec=content, file_name=file_name, use_global_path=use_global_path, force=True, debug=False)
    if debug:
        print_debug(f"SPG file {file_name} reformatted in {(time.perf_counter() - start_time):.6f} seconds")
