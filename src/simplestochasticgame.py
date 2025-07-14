import os
import re
import time

from fractions import Fraction
from error_handling import print_warning, print_error, print_debug, is_float_expr, float_or_fraction
from settings import GLOBAL_DEBUG, PRINT_VERTEX_CREATION_WARNINGS, ENSURE_EVE_AND_ADAM_VERTICES, GLOBAL_IN_OUT_PATH, USE_EXACT_ARITHMETIC, MAX_DENOMINATOR


class SsgVertex:

    def __init__(self, name: str, is_eve: bool, is_target: bool):
        """
        Creates a vertex of a simple stochastic game.
        :param name: Name of the vertex
        :type name: str
        :param is_eve: True if the vertex is controlled by Eve, False if it is controlled by Adam
        :type is_eve: bool
        :param is_target: True if the vertex is a target vertex, False otherwise
        :type is_target: bool
        """
        self.name = name
        self.is_eve = is_eve
        self.is_target = is_target

    def __str__(self):
        """
        Returns a string representation of the vertex.
        :return: String representation of the vertex
        :rtype: str
        """
        if self.is_eve:
            if self.is_target:
                return f"( {self.name} | E | T )"
            else:
                return f"( {self.name} | E | N )"
        else:
            if self.is_target:
                return f"( {self.name} | A | T )"
            else:
                return f"( {self.name} | A | N )"


class SsgTransition:
    def __init__(self, start_vertex: SsgVertex, end_vertices: set[tuple[float | Fraction, SsgVertex]], action: str):
        """
        Creates a transition of a simple stochastic game.
        :param start_vertex: Starting vertex of the transition
        :type start_vertex: SsgVertex
        :param end_vertices: Set of tuples of probabilities and respective end vertices
        :type end_vertices: set[(float | Fraction, SsgVertex)]
        :param action:
        :type action: str
        """
        self.start_vertex = start_vertex
        self.end_vertices = end_vertices
        self.action = action
        total_prob = 0
        neg_probs = False
        for prob, vert in end_vertices:
            if prob < 0:
                neg_probs = True
            total_prob += prob
        if abs(total_prob-1) > 0.0001:
            print_warning(f"Sum ({total_prob}) of probabilities does not equal 1 of edge from {self.start_vertex.name} with action {self.action}")
        if neg_probs:
            print_warning(f"There is at least one probability that is negative of edge from {self.start_vertex.name} with action {self.action}")
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


class SimpleStochasticGame:
    def __init__(self, vertices: dict[str, SsgVertex], transitions: dict[tuple[SsgVertex, str], SsgTransition], init_vertex: SsgVertex):
        """
        Creates a simple stochastic game and checks for deadlock vertices and vertices without ingoing transitions.
        :param vertices: Vertices of the simple stochastic game
        :type vertices: dict[str, SsgVertex]
        :param transitions: Transitions of the simple stochastic game
        :type transitions: dict[(SsgVertex, str), SsgTransition]
        :param init_vertex: Initial vertex of the simple stochastic game
        :type init_vertex: SsgVertex
        """
        self.vertices = vertices
        self.transitions = transitions
        self.init_vertex = init_vertex

        if ENSURE_EVE_AND_ADAM_VERTICES:
            has_eve = False
            has_adam = False
            for vertex in self.vertices.values():
                if vertex.is_eve:
                    has_eve = True
                else:
                    has_adam = True
            if not has_eve:
                self.add_extra_vert(is_eve=True, is_target=False)
                if GLOBAL_DEBUG:
                    print_debug("No Eve vertex was found. An extra Eve vertex was added.")
            if not has_adam:
                self.add_extra_vert(is_eve=False, is_target=False)
                if GLOBAL_DEBUG:
                    print_debug("No Adam vertex was found. An extra Adam vertex was added.")
        for vertex in self.vertices.values():
            if GLOBAL_DEBUG and PRINT_VERTEX_CREATION_WARNINGS and not has_ssg_vertex_ingoing_transition(vertex, self.transitions):
                print_debug(f"Vertex {vertex.name} has no ingoing transition.")
            if is_deadlock_vertex(vertex, self.transitions):
                self.transitions[vertex, "selfloop"] = SsgTransition(vertex, {(1.0, vertex)}, "selfloop")
                if GLOBAL_DEBUG and PRINT_VERTEX_CREATION_WARNINGS:
                    print_debug(f"Vertex {vertex.name} is a deadlock vertex. A selfloop was added.")
        for vertex_name in vertices:
            if vertex_name != vertices[vertex_name].name:
                print_error(
                    f"Key {vertex_name} in vertices dictionary does not match vertex name {vertices[vertex_name].name}. This is needed for the SSG to work correctly.")
        for transition_key in transitions:
            if transition_key[0] is not transitions[transition_key].start_vertex:
                print_error(
                    f"Key {transition_key[0]} in transitions dictionary does not match transition start vertex {transitions[transition_key].start_vertex}. This is needed for the SSG to work correctly.")
            if transition_key[1] != transitions[transition_key].action:
                print_error(
                    f"Key {transition_key[1]} in transitions dictionary does not match transition action {transitions[transition_key].action}. This is needed for the SSG to work correctly.")

    def add_extra_vert(self, is_eve: bool, is_target: bool = False) -> SsgVertex:
        """
        Adds an extra vertex to the simple stochastic game.
        :param is_eve: True if the new vertex is controlled by Eve, False if it is controlled by Adam
        :type is_eve: bool
        :param is_target: True if the new vertex is a target vertex, False otherwise
        :type is_target: bool
        :return: Newly created vertex
        :rtype: SsgVertex
        """
        i = 1
        while f"extra{i}" in self.vertices:
            i += 1
        new_vertex = SsgVertex(f"extra{i}", is_eve, is_target)
        self.vertices[f"extra{i}"] = new_vertex
        return new_vertex

    def has_action(self, action: str) -> bool:
        """
        Checks if the simple stochastic game has a transition with the given action.
        :param action: Action to check
        :return: True if the action exists, False otherwise
        """
        for transition in self.transitions.values():
            if transition.action == action:
                return True
        return False

    def has_alpha_underflow(self) -> bool:
        """
        Checks if the stochastic parity game has an alpha underflow.
        :return: 'True' if the game has an alpha underflow, False otherwise
        :rtype: bool
        """
        for transition in self.transitions.values():
            for prob, end_vertex in transition.end_vertices:
                if prob <= 0:
                    return True
        return False


def has_ssg_vertex_ingoing_transition(vertex: SsgVertex, transitions: dict[tuple[SsgVertex, str], SsgTransition]) -> bool:
    """
    Checks if the given vertex has an ingoing transitions.
    :param vertex: Vertex to check
    :type vertex: SsgVertex
    :param transitions: Transitions of the simple stochastic game
    :type transitions: dict[(SsgVertex, str), SsgTransition]
    :return: True if the vertex has ingoing transitions, False otherwise
    :rtype: bool
    """
    for transition in transitions.values():
        for end_vertex in transition.end_vertices:
            if end_vertex[1] == vertex:
                return True
    return False


def is_deadlock_vertex(vertex: SsgVertex, transitions: dict[tuple[SsgVertex, str], SsgTransition]) -> bool:
    """
    Checks if the given vertex is a deadlock vertex.
    :param vertex: Vertex to check
    :type vertex: SsgVertex
    :param transitions: Transitions of the simple stochastic game
    :type transitions: dict[(SsgVertex, str), SsgTransition]
    :return: True if the vertex is a deadlock vertex, False otherwise
    :rtype: bool
    """
    for transition in transitions.values():
        if transition.start_vertex == vertex:
            return False
    return True


def create_extra_vert(vertices: set[SsgVertex], is_eve: bool, is_target: bool = False) -> SsgVertex:
    """
    Creates an extra vertex for an SSG set without adding it.
    :param vertices: Set of vertices that the new vertex should not conflict with
    :type vertices: set[SsgVertex]
    :param is_eve: True if the new vertex is controlled by Eve, False if it is controlled by Adam
    :type is_eve: bool
    :param is_target: True if the new vertex is a target vertex, False otherwise
    :type is_target: bool
    :return: Newly created vertex
    :rtype: SsgVertex
    """
    i = 1
    while True:
        new_name = f"extra{i}"
        name_available = True
        for vertex in vertices:
            if vertex.name == new_name:
                i += 1
                name_available = False
                break
        if name_available:
            break

    new_vertex = SsgVertex(f"extra{i}", is_eve, is_target)
    return new_vertex


def has_transition_end_vertex(transition: SsgTransition, end_vertex: SsgVertex) -> bool:
    """
    Checks if the given transition has an end vertex that matches the given end vertex.
    :param transition: Transition to check
    :type transition: SsgTransition
    :param end_vertex: Vertex to check for in the transition's end vertices
    :type end_vertex: SsgVertex
    :return: Whether the transition has the end vertex
    :rtype: bool
    """
    for prob, vertex in transition.end_vertices:
        if vertex == end_vertex:
            return True
    return False


def read_ssg_from_file(file_name, use_global_path: bool = False, debug: bool = GLOBAL_DEBUG) -> SimpleStochasticGame:
    """
    Reads a simple stochastic game from a file and returns the corresponding SimpleStochasticGame object.
    :param file_name: Path to the file that is joined with the global global_in_out_path
    :type file_name: str
    :param use_global_path: If True, the file name is joined with the global global_in_out_path
    :type use_global_path: bool
    :param debug: True if debug information should be printed
    :type debug: bool
    :return: SimpleStochasticGame object
    :rtype: SimpleStochasticGame
    """
    if debug:
        start_time = time.perf_counter()
    if use_global_path:
        file_name = os.path.join(GLOBAL_IN_OUT_PATH, file_name)
    if file_name[-4:] != ".ssg":
        print_error("Not a .ssg file")
    try:
        with open(file_name, "r") as file:
            content = file.readlines()
    except FileNotFoundError:
        print_error(f"File '{file_name}' not found.")
    except Exception as e:
        print_error(f"Could not read the file: {e}")

    if content[0] != "ssg\n":
        print_error("Not an SSG specification.")

    state = 0
    ssg_vertices = dict()
    ssg_initial_vertex = None
    ssg_transitions = dict()
    for current_line_index in range(1, len(content)):
        current_line = re.split(r"\s+", content[current_line_index].replace("\t", " ").replace("\n", " ").replace(":", " : ").replace("|", " | ").replace("+", " + ").strip())
        match state:
            case 0:
                if current_line == [""]:
                    continue
                if current_line == ["evevertices"]:
                    state = 1
                    continue
                print_error(f"File does not comply with SSG specification. Line {current_line_index+1}: {content[current_line_index]}")

            case 1:
                if current_line == [""]:
                    continue
                if current_line == ["endevevertices"]:
                    state = 2
                    continue
                if len(current_line) == 1:
                    if current_line[0] in ssg_vertices:
                        print_error(f"Duplicate vertex {current_line[0]}")
                    ssg_vertices[current_line[0]] = SsgVertex(current_line[0], True, False)
                    # print(ssg_vertices[current_line[0]])
                    continue
                if (current_line[1] == "T" or current_line[1] == "t") and len(current_line) == 2:
                    if current_line[0] in ssg_vertices:
                        print_error(f"Duplicate vertex {current_line[0]}")
                    ssg_vertices[current_line[0]] = SsgVertex(current_line[0], True, True)
                    # print(ssg_vertices[current_line[0]])
                    continue
                print_error(f"File does not comply with SSG specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 2:
                if current_line == [""]:
                    continue
                if current_line == ["adamvertices"]:
                    state = 3
                    continue
                print_error(f"File does not comply with SSG specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 3:
                if current_line == [""]:
                    continue
                if current_line == ["endadamvertices"]:
                    state = 4
                    continue
                if len(current_line) == 1:
                    if current_line[0] in ssg_vertices:
                        print_error(f"Duplicate vertex {current_line[0]}")
                    ssg_vertices[current_line[0]] = SsgVertex(current_line[0], False, False)
                    continue
                if (current_line[1] == "T" or current_line[1] == "t") and len(current_line) == 2:
                    if current_line[0] in ssg_vertices:
                        print_error(f"Duplicate vertex {current_line[0]}")
                    ssg_vertices[current_line[0]] = SsgVertex(current_line[0], False, True)
                    continue
                print_error(
                    f"File does not comply with SSG specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 4:
                if current_line == [""]:
                    continue
                if len(current_line) == 3 and current_line[0] == "initialvertex" and current_line[1] == ":":
                    if current_line[2] not in ssg_vertices:
                        print_error(f"Initial vertex {current_line[2]} was not declared before")
                    ssg_initial_vertex = ssg_vertices[current_line[2]]
                    state = 5
                    continue
                print_error(f"File does not comply with SSG specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 5:
                if current_line == [""]:
                    continue
                if current_line == ["transitions"]:
                    state = 6
                    continue
                print_error(f"File does not comply with SSG specification. Line {current_line_index + 1}: {content[current_line_index]}")
            case 6:
                if current_line == [""]:
                    continue
                if current_line == ["endtransitions"]:
                    break
                if len(current_line) == 4 and current_line[2] == ":":
                    if not (current_line[0] in ssg_vertices):
                        print_error(f"{current_line[0]} from transition {content[current_line_index]} was not specified as a vertex")
                    if not (current_line[3] in ssg_vertices):
                        print_error(f"{current_line[2]} from transition {content[current_line_index]} was not specified as a vertex")
                    if (ssg_vertices[current_line[0]], current_line[1]) in ssg_transitions:
                        print_error(f"Duplicate transition from {ssg_vertices[current_line[0]]} with action {current_line[1]}")
                    ssg_transitions[(ssg_vertices[current_line[0]], current_line[1])] = SsgTransition(ssg_vertices[current_line[0]], {(1.0, ssg_vertices[current_line[3]])}, current_line[1])
                    continue
                if len(current_line) >= 6 and len(current_line) % 4 == 2:
                    if not (current_line[0] in ssg_vertices):
                        print_error(f"{current_line[0]} from transition {content[current_line_index]} was not specified as a vertex")
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
                            if not (current_line[i] in ssg_vertices):
                                print_error(f"{current_line[i]} from transition {content[current_line_index]} was not specified as a vertex")
                        elif i % 4 == 2:
                            if current_line[i] != "+":
                                print_error(f"Expected \"+\" in transition {content[current_line_index]}")
                    if (ssg_vertices[current_line[0]], current_line[1]) in ssg_transitions:
                        print_error(f"Duplicate transition from {ssg_vertices[current_line[0]]} with action {current_line[1]}")
                    end_vertices = set()
                    for i in range(0, int((len(current_line)-2)/4)):
                        end_vertices.add((float(eval(current_line[3+i*4])), ssg_vertices[current_line[5+i*4]]))
                    ssg_transitions[(ssg_vertices[current_line[0]], current_line[1])] = SsgTransition(ssg_vertices[current_line[0]], end_vertices, current_line[1])
                    continue
                print_error(f"File does not comply with SSG specification. Line {current_line_index + 1}: {content[current_line_index]}")
            case _:
                print_error("Undefined state")
    if debug:
        print_debug(f"SSG file {file_name} read in {(time.perf_counter() - start_time):.6f} seconds")
    return SimpleStochasticGame(ssg_vertices, ssg_transitions, ssg_initial_vertex)


def ssg_to_ssgspec(ssg: SimpleStochasticGame) -> str:
    """
    Converts a SimpleStochasticGame object to a string representation in the ssg specification format.
    :param ssg: The SimpleStochasticGame object to convert
    :type ssg: SimpleStochasticGame
    :return: SSG specification string
    :rtype: str
    """
    content = "ssg\n\n"
    eve_vertices = "evevertices\n"
    adam_vertices = "adamvertices\n"
    for vertex in ssg.vertices.values():
        if vertex.is_target:
            line = f"\t{vertex.name} T\n"
        else:
            line = f"\t{vertex.name}\n"
        if vertex.is_eve:
            eve_vertices += line
        else:
            adam_vertices += line
    eve_vertices += "endevevertices\n\n"
    adam_vertices += "endadamvertices\n\n"
    content += eve_vertices + adam_vertices
    content += f"initialvertex : {ssg.init_vertex.name}\n\n"
    content += "transitions\n"
    for vert_act, trans in ssg.transitions.items():
        if len(trans.end_vertices) == 1:
            content += f"\t{vert_act[0].name} {vert_act[1]} : {next(iter(trans.end_vertices))[1].name}\n"
        else:
            transition_str = f"\t{vert_act[0].name} {vert_act[1]} : "
            for end_vert in trans.end_vertices:
                transition_str += f"{float_or_fraction(end_vert[0], 100000)} | {end_vert[1].name} + "
            transition_str = transition_str[:-3] + "\n"
            content += transition_str
    content += "endtransitions"
    return content


def save_ssg_file(ssg_spec: str, file_name: str = "", use_global_path: bool = False, force: bool = False, debug: bool = GLOBAL_DEBUG):
    """
    Saves the given content to a file with the given name. If the file already exists and force is not set to True, nothing is changed.
    :param ssg_spec: SSG specification to save
    :type ssg_spec: str
    :param file_name: Name of the file to save the SSG specification to
    :type file_name: str
    :param use_global_path: True if the file name should be joined with the global global_in_out_path
    :type use_global_path: bool
    :param force: True if the file should be overwritten if it already exists
    :type force: bool
    :param debug: True if debug information should be printed
    :type debug: bool
    """
    if debug:
        start_time = time.perf_counter()
    if not file_name:
        file_name = "out.ssg"
    if use_global_path:
        file_name = os.path.join(GLOBAL_IN_OUT_PATH, file_name)
    if not file_name.endswith(".ssg"):
        print_warning(f"File {file_name} is not an .ssg file. Nothing was changed")
    elif not force and os.path.exists(file_name) and os.path.getsize(file_name) != 0:
        print_warning(f"File {file_name} already exists. Nothing was changed")
    else:
        with open(file_name, "w") as file:
            file.write(ssg_spec)
            if debug:
                print_debug(f"SSG file {file_name} saved successfully")
    if debug:
        print_debug(f"SSG file {file_name} created in {(time.perf_counter() - start_time):.6f} seconds")


def reformat_ssgspec(file_name: str, use_global_path: bool = False, debug: bool = GLOBAL_DEBUG):
    """
    Reformats the SSG specification file to the default format.
    :param file_name: Name of the file to reformat
    :type file_name: str
    :param use_global_path: True if the file name should be joined with the global global_in_out_path
    :type use_global_path: bool
    :param debug: True if debug information should be printed
    :type debug: bool
    """
    if debug:
        start_time = time.perf_counter()
    if use_global_path:
        file_name = os.path.join(GLOBAL_IN_OUT_PATH, file_name)
    ssg = read_ssg_from_file(file_name=file_name, use_global_path=use_global_path, debug=False)
    content = ssg_to_ssgspec(ssg)
    save_ssg_file(ssg_spec=content, file_name=file_name, use_global_path=use_global_path, force=True, debug=False)
    if debug:
        print_debug(f"SSG file {file_name} reformatted in {(time.perf_counter() - start_time):.6f} seconds")
