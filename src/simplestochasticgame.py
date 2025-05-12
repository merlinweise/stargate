import sys
import re
import os
from error_handling import print_warning, print_error, is_float_expr


class SsgVertex:

    def __init__(self, name: str, is_eve: bool, is_target: bool):
        self.name = name
        self.is_eve = is_eve
        self.is_target = is_target

    def __str__(self):
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


class SsgTransition:

    def __init__(self, start_vertex: SsgVertex, end_vertices: set[(float, SsgVertex)], action: str):
        self.start_vertex = start_vertex
        self.end_vertices = end_vertices
        self.action = action
        total_prob: float = 0
        neg_probs = False
        for prob, vert in end_vertices:
            if prob < 0:
                neg_probs = True
            total_prob += prob
        if total_prob != 1:
            print_warning(f"Sum ({total_prob}) of probabilities does not equal 1 of edge from {self.start_vertex.name} "
                          f"with action {self.action}")
        if neg_probs:
            print_warning(f"There is at least one probability that is negative of edge from {self.start_vertex.name} "
                          f"with action {self.action}")

    def __str__(self):
        output = f"Starting Vertex: {self.start_vertex}, Action: {self.action}, "

        for prob, vert in self.end_vertices:
            output += f"{prob}: to {vert.name} , "
        output = output[:-3]
        return output


class SimpleStochasticGame:
    def __init__(self, vertices: dict[str, SsgVertex], transitions: dict[(SsgVertex, str), SsgTransition], init_vertex):
        self.vertices = vertices
        self.transitions = transitions
        self.init_vertex = init_vertex

        for vertex in self.vertices.values():
            if not has_ssg_vertex_ingoing_transition(vertex, self.transitions):
                print_warning(f"Vertex {vertex.name} has no ingoing transition")
            if is_deadlock_vertex(vertex, self.transitions):
                print_warning(f"Vertex {vertex.name} is a deadlock vertex")
                self.transitions[vertex, "selfloop"] = SsgTransition(vertex, {(1.0, vertex)}, "selfloop")

    def add_extra_vert(self, is_eve: bool, is_target: bool = False) -> SsgVertex:
        i = 1
        while f"extra{i}" in self.vertices:
            i += 1
        new_vertex = SsgVertex(f"extra{i}", is_eve, is_target)
        self.vertices[f"extra{i}"] = new_vertex
        return new_vertex

    def has_action(self, action: str) -> bool:
        for transition in self.transitions.values():
            if transition.action == action:
                return True
        return False


def has_ssg_vertex_ingoing_transition(vertex: SsgVertex, transitions: dict[(SsgVertex, str), SsgTransition]) -> bool:
    for transition in transitions.values():
        for end_vertex in transition.end_vertices:
            if end_vertex[1] == vertex:
                return True
    return False


def is_deadlock_vertex(vertex: SsgVertex, transitions: dict[(SsgVertex, str), SsgTransition]) -> bool:
    for transition in transitions.values():
        if transition.start_vertex == vertex:
            return False
    return True


def read_ssg_from_file(file_name: str) -> SimpleStochasticGame:
    if file_name[-4:] != ".ssg":
        print_error("Not a .ssg file")
    try:
        with open(file_name, "r", encoding="utf-8") as file:
            content = file.readlines()
    except FileNotFoundError:
        print_error(f"File '{file_name}' not found.")
    except Exception as e:
        print_error(f"Could not read the file: {e}")

    if content[0]!="ssg\n":
        print_error("Not an ssg specification.")

    state=0
    ssg_vertices = dict()
    ssg_initial_vertex = None
    ssg_transitions = dict()
    for current_line_index in range(1,len(content)):
        current_line = re.split(r"\s+", content[current_line_index].replace("\t", " ").replace("\n", " ").replace(":"," : ").replace("|"," | ").replace("+"," + ").strip())
        # print(current_line)

        match state:
            case 0:
                if current_line == [""]:
                    continue
                if current_line == ["evevertices"]:
                    state=1
                    continue
                print_error(f"File does not comply with ssg specification. Line {current_line_index+1}: {content[current_line_index]}")

            case 1:
                if current_line == [""]:
                    continue
                if current_line == ["endevevertices"]:
                    state=2
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
                print_error(f"File does not comply with ssg specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 2:
                if current_line == [""]:
                    continue
                if current_line == ["adamvertices"]:
                    state=3
                    continue
                print_error(f"File does not comply with ssg specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 3:
                if current_line == [""]:
                    continue
                if current_line == ["endadamvertices"]:
                    state=4
                    continue
                if len(current_line) == 1:
                    if current_line[0] in ssg_vertices:
                        print_error(f"Duplicate vertex {current_line[0]}")
                    ssg_vertices[current_line[0]] = SsgVertex(current_line[0], False, False)
                    # print(ssg_vertices[current_line[0]])
                    continue
                if (current_line[1] == "T" or current_line[1] == "t") and len(current_line) == 2:
                    if current_line[0] in ssg_vertices:
                        print_error(f"Duplicate vertex {current_line[0]}")
                    ssg_vertices[current_line[0]] = SsgVertex(current_line[0], False, True)
                    # print(ssg_vertices[current_line[0]])
                    continue
                print_error(
                    f"File does not comply with ssg specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 4:
                if current_line == [""]:
                    continue
                if len(current_line) == 3 and current_line[0] == "initialvertex" and current_line[1] == ":":
                    if current_line[2] not in ssg_vertices:
                        print_error(f"Initial vertex {current_line[2]} was not declared before")
                    ssg_initial_vertex = ssg_vertices[current_line[2]]
                    # print(ssg_inital_vertex)
                    state = 5
                    continue
                print_error(f"File does not comply with ssg specification. Line {current_line_index + 1}: {content[current_line_index]}")

            case 5:
                if current_line == [""]:
                    continue
                if current_line == ["transitions"]:
                    state = 6
                    continue
                print_error(f"File does not comply with ssg specification. Line {current_line_index + 1}: {content[current_line_index]}")
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
                    #print(ssg_transitions[(ssg_vertices[current_line[0]], current_line[1])])
                    continue
                if len(current_line) >= 6 and len(current_line) % 4 == 2 :
                    if not (current_line[0] in ssg_vertices):
                        print_error(f"{current_line[0]} from transition {content[current_line_index]} was not specified as a vertex")
                    if current_line[2] != ":":
                        print_error(f"Expected \":\" in transition {content[current_line_index]}")
                    for i in range(3,len(current_line)):
                        if i % 4 == 3:
                            if not (is_float_expr(current_line[i])):
                                print_error(f"Expected float in transition {content[current_line_index]}")
                        elif i % 4 == 0:
                            if current_line[i] != "|":
                                print_error(f"Expected \"|\" in transition {content[current_line_index]}")
                        elif i % 4 == 1:
                            if not(current_line[i] in ssg_vertices):
                                print_error(f"{current_line[i]} from transition {content[current_line_index]} was not specified as a vertex")
                        elif i % 4 == 2:
                            if current_line[i] != "+":
                                print_error(f"Expected \"+\" in transition {content[current_line_index]}")
                    if (ssg_vertices[current_line[0]], current_line[1]) in ssg_transitions:
                        print_error(f"Duplicate transition from {ssg_vertices[current_line[0]]} with action {current_line[1]}")
                    end_vertices = set()
                    for i in range(0,int((len(current_line)-2)/4)):
                        end_vertices.add((float(eval(current_line[3+i*4])),ssg_vertices[current_line[5+i*4]]))
                    ssg_transitions[(ssg_vertices[current_line[0]], current_line[1])] = SsgTransition(ssg_vertices[current_line[0]], end_vertices, current_line[1])
                    continue
                print_error(f"File does not comply with ssg specification. Line {current_line_index + 1}: {content[current_line_index]}")
            case _:
                print_error("Undefined state")
                sys.exit(1)
    return SimpleStochasticGame(ssg_vertices, ssg_transitions, ssg_initial_vertex)


def ssg_to_ssgspec(ssg: SimpleStochasticGame, file_name: str = "", force: bool = False) -> str:
    content = "ssg\n\n"
    eve_vertices = "evevertices\n"
    adam_vertices = "adamvertices\n"
    for vertex in ssg.vertices.values():
        line = ""
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
        if len(trans.end_vertices)==1:
            content += f"\t{vert_act[0].name} {vert_act[1]} : {next(iter(trans.end_vertices))[1].name}\n"
        else:
            transition_str = f"\t{vert_act[0].name} {vert_act[1]} : "
            for end_vert in trans.end_vertices:
                transition_str += f"{str(end_vert[0])} | {end_vert[1].name} + "
            transition_str = transition_str[:-3] + "\n"
            content += transition_str
    content += "endtransitions"

    if file_name:
        if not file_name.endswith(".ssg"):
            print_warning("File is not an .ssg file. Nothing was changed")
        elif not force and os.path.exists(file_name) and os.path.getsize(file_name) != 0:
            print_warning("File already exists. Nothing was changed")
        else:
            with open(file_name, "w", encoding="utf-8") as file:
                file.write(content)
    return content


def reformat_ssgspec(file_name: str):
    ssg = read_ssg_from_file(file_name)
    ssg_to_ssgspec(ssg, file_name, True)
