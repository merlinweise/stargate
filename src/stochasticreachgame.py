import os
import re
import time

from error_handling import print_warning, print_error, print_debug, is_float_expr, float_or_fraction
from settings import GLOBAL_DEBUG, PRINT_VERTEX_CREATION_WARNINGS, ENSURE_EVE_AND_ADAM_VERTICES, GLOBAL_IN_OUT_PATH


class SrgVertex:

    def __init__(self, name: str, is_eve: bool, is_target: bool):
        """
        Creates a vertex of a stochastic reach game.
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
                return f"Eve Target-Node {self.name}"
            else:
                return f"Eve Non-Target-Node {self.name}"
        else:
            if self.is_target:
                return f"Adam Target-Node {self.name}"
            else:
                return f"Adam Non-Target-Node {self.name}"


class SrgTransition:
    def __init__(self, start_vertex: SrgVertex, end_vertices: set[tuple[float, SrgVertex]], action: str):
        """
        Creates a transition of a stochastic reach game.
        :param start_vertex: Starting vertex of the transition
        :type start_vertex: SrgVertex
        :param end_vertices: Set of tuples of probabilities and respective end vertices
        :type end_vertices: set[(float, SrgVertex)]
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

    def __str__(self):
        """
        Returns a string representation of the transition.
        :return: String representation of the transition
        :rtype: str
        """
        output = f"Starting Vertex: {self.start_vertex}, Action: {self.action}, "

        for prob, vert in self.end_vertices:
            output += f"{prob}: to {vert.name} , "
        output = output[:-3]
        return output


class StochasticReachGame:
    def __init__(self, vertices: dict[str, SrgVertex], transitions: dict[tuple[SrgVertex, str], SrgTransition], init_vertex: SrgVertex):
        """
        Creates a stochastic reach game and checks for deadlock vertices and vertices without ingoing transitions.
        :param vertices: Vertices of the stochastic reach game
        :type vertices: dict[str, SrgVertex]
        :param transitions: Transitions of the stochastic reach game
        :type transitions: dict[(SrgVertex, str), SrgTransition]
        :param init_vertex: Initial vertex of the stochastic reach game
        :type init_vertex: SrgVertex
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
            if GLOBAL_DEBUG and PRINT_VERTEX_CREATION_WARNINGS and not has_srg_vertex_ingoing_transition(vertex, self.transitions):
                print_debug(f"Vertex {vertex.name} has no ingoing transition.")
            if is_deadlock_vertex(vertex, self.transitions):
                self.transitions[vertex, "selfloop"] = SrgTransition(vertex, {(1.0, vertex)}, "selfloop")
                if GLOBAL_DEBUG and PRINT_VERTEX_CREATION_WARNINGS:
                    print_debug(f"Vertex {vertex.name} is a deadlock vertex. A selfloop was added.")

    def add_extra_vert(self, is_eve: bool, is_target: bool = False) -> SrgVertex:
        """
        Adds an extra vertex to the stochastic reach game.
        :param is_eve: True if the new vertex is controlled by Eve, False if it is controlled by Adam
        :type is_eve: bool
        :param is_target: True if the new vertex is a target vertex, False otherwise
        :type is_target: bool
        :return: Newly created vertex
        :rtype: SrgVertex
        """
        i = 1
        while f"extra{i}" in self.vertices:
            i += 1
        new_vertex = SrgVertex(f"extra{i}", is_eve, is_target)
        self.vertices[f"extra{i}"] = new_vertex
        return new_vertex

    def has_action(self, action: str) -> bool:
        """
        Checks if the stochastic reach game has a transition with the given action.
        :param action: Action to check
        :return: True if the action exists, False otherwise
        """
        for transition in self.transitions.values():
            if transition.action == action:
                return True
        return False


def has_srg_vertex_ingoing_transition(vertex: SrgVertex, transitions: dict[tuple[SrgVertex, str], SrgTransition]) -> bool:
    """
    Checks if the given vertex has an ingoing transitions.
    :param vertex: Vertex to check
    :type vertex: SrgVertex
    :param transitions: Transitions of the stochastic reach game
    :type transitions: dict[(SrgVertex, str), SrgTransition]
    :return: True if the vertex has ingoing transitions, False otherwise
    :rtype: bool
    """
    for transition in transitions.values():
        for end_vertex in transition.end_vertices:
            if end_vertex[1] == vertex:
                return True
    return False


def is_deadlock_vertex(vertex: SrgVertex, transitions: dict[tuple[SrgVertex, str], SrgTransition]) -> bool:
    """
    Checks if the given vertex is a deadlock vertex.
    :param vertex: Vertex to check
    :type vertex: SrgVertex
    :param transitions: Transitions of the stochastic reach game
    :type transitions: dict[(SrgVertex, str), SrgTransition]
    :return: True if the vertex is a deadlock vertex, False otherwise
    :rtype: bool
    """
    for transition in transitions.values():
        if transition.start_vertex == vertex:
            return False
    return True


def read_srg_from_file(file_name, use_global_path: bool = False, debug: bool = GLOBAL_DEBUG) -> StochasticReachGame:
    """
    Reads a stochastic reach game from a file and returns the corresponding StochasticReachGame object.
    :param file_name: Path to the file that is joined with the global global_in_out_path
    :type file_name: str
    :param use_global_path: If True, the file name is joined with the global global_in_out_path
    :type use_global_path: bool
    :param debug: True if debug information should be printed
    :type debug: bool
    :return: StochasticReachGame object
    :rtype: StochasticReachGame
    """
    if debug:
        start_time = time.perf_counter()
    if use_global_path:
        file_name = os.path.join(GLOBAL_IN_OUT_PATH, file_name)
    if file_name[-4:] != ".srg":
        print_error("Not a .srg file")
    try:
        with open(file_name, "r") as file:
            content = file.readlines()
    except FileNotFoundError:
        print_error(f"File '{file_name}' not found.")
    except Exception as e:
        print_error(f"Could not read the file: {e}")

    if content[0] != "srg\n":
        print_error("Not an srg specification.")

    state = 0
    srg_vertices = dict()
    srg_initial_vertex = None
    srg_transitions = dict()
    for current_line_index in range(1, len(content)):
        current_line = re.split(r"\s+", content[current_line_index].replace("\t", " ").replace("\n", " ").replace(":", " : ").replace("|", " | ").replace("+", " + ").strip())
        match state:
            case 0:
                if current_line == [""]:
                    continue
                if current_line == ["evevertices"]:
                    state = 1
                    continue
                print_error(f"File does not comply with srg specification. Line {current_line_index+1}: {content[current_line_index]}")

            case 1:
                if current_line == [""]:
                    continue
                if current_line == ["endevevertices"]:
                    state = 2
                    continue
                if len(current_line) == 1:
                    if current_line[0] in srg_vertices:
                        print_error(f"Duplicate vertex {current_line[0]}")
                    srg_vertices[current_line[0]] = SrgVertex(current_line[0], True, False)
                    # print(srg_vertices[current_line[0]])
                    continue
                if (current_line[1] == "T" or current_line[1] == "t") and len(current_line) == 2:
                    if current_line[0] in srg_vertices:
                        print_error(f"Duplicate vertex {current_line[0]}")
                    srg_vertices[current_line[0]] = SrgVertex(current_line[0], True, True)
                    # print(srg_vertices[current_line[0]])
                    continue
                print_error(f"File does not comply with srg specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 2:
                if current_line == [""]:
                    continue
                if current_line == ["adamvertices"]:
                    state = 3
                    continue
                print_error(f"File does not comply with srg specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 3:
                if current_line == [""]:
                    continue
                if current_line == ["endadamvertices"]:
                    state = 4
                    continue
                if len(current_line) == 1:
                    if current_line[0] in srg_vertices:
                        print_error(f"Duplicate vertex {current_line[0]}")
                    srg_vertices[current_line[0]] = SrgVertex(current_line[0], False, False)
                    continue
                if (current_line[1] == "T" or current_line[1] == "t") and len(current_line) == 2:
                    if current_line[0] in srg_vertices:
                        print_error(f"Duplicate vertex {current_line[0]}")
                    srg_vertices[current_line[0]] = SrgVertex(current_line[0], False, True)
                    continue
                print_error(
                    f"File does not comply with srg specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 4:
                if current_line == [""]:
                    continue
                if len(current_line) == 3 and current_line[0] == "initialvertex" and current_line[1] == ":":
                    if current_line[2] not in srg_vertices:
                        print_error(f"Initial vertex {current_line[2]} was not declared before")
                    srg_initial_vertex = srg_vertices[current_line[2]]
                    state = 5
                    continue
                print_error(f"File does not comply with srg specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 5:
                if current_line == [""]:
                    continue
                if current_line == ["transitions"]:
                    state = 6
                    continue
                print_error(f"File does not comply with srg specification. Line {current_line_index + 1}: {content[current_line_index]}")
            case 6:
                if current_line == [""]:
                    continue
                if current_line == ["endtransitions"]:
                    break
                if len(current_line) == 4 and current_line[2] == ":":
                    if not (current_line[0] in srg_vertices):
                        print_error(f"{current_line[0]} from transition {content[current_line_index]} was not specified as a vertex")
                    if not (current_line[3] in srg_vertices):
                        print_error(f"{current_line[2]} from transition {content[current_line_index]} was not specified as a vertex")
                    if (srg_vertices[current_line[0]], current_line[1]) in srg_transitions:
                        print_error(f"Duplicate transition from {srg_vertices[current_line[0]]} with action {current_line[1]}")
                    srg_transitions[(srg_vertices[current_line[0]], current_line[1])] = SrgTransition(srg_vertices[current_line[0]], {(1.0, srg_vertices[current_line[3]])}, current_line[1])
                    continue
                if len(current_line) >= 6 and len(current_line) % 4 == 2:
                    if not (current_line[0] in srg_vertices):
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
                            if not (current_line[i] in srg_vertices):
                                print_error(f"{current_line[i]} from transition {content[current_line_index]} was not specified as a vertex")
                        elif i % 4 == 2:
                            if current_line[i] != "+":
                                print_error(f"Expected \"+\" in transition {content[current_line_index]}")
                    if (srg_vertices[current_line[0]], current_line[1]) in srg_transitions:
                        print_error(f"Duplicate transition from {srg_vertices[current_line[0]]} with action {current_line[1]}")
                    end_vertices = set()
                    for i in range(0, int((len(current_line)-2)/4)):
                        end_vertices.add((float(eval(current_line[3+i*4])), srg_vertices[current_line[5+i*4]]))
                    srg_transitions[(srg_vertices[current_line[0]], current_line[1])] = SrgTransition(srg_vertices[current_line[0]], end_vertices, current_line[1])
                    continue
                print_error(f"File does not comply with SRG specification. Line {current_line_index + 1}: {content[current_line_index]}")
            case _:
                print_error("Undefined state")
    if debug:
        print_debug(f"SRG file {file_name} read in {(time.perf_counter() - start_time):.6f} seconds")
    return StochasticReachGame(srg_vertices, srg_transitions, srg_initial_vertex)


def srg_to_srgspec(srg: StochasticReachGame) -> str:
    """
    Converts a StochasticReachGame object to a string representation in the srg specification format.
    :param srg: The StochasticReachGame object to convert
    :type srg: StochasticReachGame
    :return: SRG specification string
    :rtype: str
    """
    content = "srg\n\n"
    eve_vertices = "evevertices\n"
    adam_vertices = "adamvertices\n"
    for vertex in srg.vertices.values():
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
    content += f"initialvertex : {srg.init_vertex.name}\n\n"
    content += "transitions\n"
    for vert_act, trans in srg.transitions.items():
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


def save_srg_file(srg_spec: str, file_name: str = "", use_global_path: bool = False, force: bool = False, debug: bool = GLOBAL_DEBUG):
    """
    Saves the given content to a file with the given name. If the file already exists and force is not set to True, nothing is changed.
    :param srg_spec: SRG specification to save
    :type srg_spec: str
    :param file_name: Name of the file to save the SRG specification to
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
        file_name = "out.srg"
    if use_global_path:
        file_name = os.path.join(GLOBAL_IN_OUT_PATH, file_name)
    if not file_name.endswith(".srg"):
        print_warning(f"File {file_name} is not an .srg file. Nothing was changed")
    elif not force and os.path.exists(file_name) and os.path.getsize(file_name) != 0:
        print_warning(f"File {file_name} already exists. Nothing was changed")
    else:
        with open(file_name, "w") as file:
            file.write(srg_spec)
            if debug:
                print_debug(f"SRG file {file_name} saved successfully")
    if debug:
        print_debug(f"SRG file {file_name} created in {(time.perf_counter() - start_time):.6f} seconds")


def reformat_srgspec(file_name: str, use_global_path: bool = False, debug: bool = GLOBAL_DEBUG):
    """
    Reformats the SRG specification file to the default format.
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
    srg = read_srg_from_file(file_name=file_name, use_global_path=use_global_path, debug=False)
    content = srg_to_srgspec(srg)
    save_srg_file(srg_spec=content, file_name=file_name, use_global_path=use_global_path, force=True, debug=False)
    if debug:
        print_debug(f"SRG file {file_name} reformatted in {(time.perf_counter() - start_time):.6f} seconds")
