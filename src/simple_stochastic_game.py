import error_handling
import sys
import re
import fractions
import os
import copy
from error_handling import print_warning, print_error, is_float_expr

class SSG_Vertex:

    def __init__(self, name: str, is_eve: bool, is_target: bool):
        self.name = name
        self.is_eve = is_eve
        self.is_target = is_target

    def __str__(self):
        if self.is_eve:
            if self.is_target:
                return (f"Eve Target-Node {self.name}")
            else:
                return (f"Eve Non-Target-Node {self.name}")
        else:
            if self.is_target:
                return (f"Adam Target-Node {self.name}")
            else:
                return (f"Adam Non-Target-Node {self.name}")

class SSG_Transition:

    def __init__(self, start_vertex: SSG_Vertex, end_vertices: set([(float, SSG_Vertex)]), action: str):
        self.start_vertex = start_vertex
        self.end_vertices = end_vertices
        self.action = action
        sum=0
        neg_probs=False
        for prob, vert in end_vertices:
            if prob < 0:
                neg_probs=True
            sum+=prob
        if sum != 1:
            print_warning(f"Sum ({sum}) of probabilities does not equal 1 of edge from {self.start_vertex.name} with action {self.action}")
        if neg_probs:
            print_warning(f"There is at least one probability that is negative of edge from {self.start_vertex.name} with action {self.action}")

    def __str__(self):
        output=(f"Starting Vertex: {self.start_vertex}, Action: {self.action}, ")

        for prob, vert in self.end_vertices:
             output+=f"{prob}: to {vert.name} , "
        output = output[:-3]
        return output

class Simple_Stochastic_Game:
    def __init__(self, vertices: dict([(str, SSG_Vertex)]), transitions: dict([((SSG_Vertex, str),SSG_Transition)]), init_vertex):
        self.vertices = vertices
        self.transitions = transitions
        self.init_vertex = init_vertex

        for vertex in self.vertices.values():
            if not has_ingoing_transition(vertex, self.transitions):
                print_warning(f"Vertex {vertex.name} has no ingoing transition")
            if is_deadlock_vertex(vertex, self.transitions):
                print_warning(f"Vertex {vertex.name} is a deadlock vertex")
                self.transitions[vertex, "selfloop"] = SSG_Transition(vertex, {(1.0, vertex)}, "selfloop")

    def add_extra_vert(self, is_eve: bool, is_target: bool=False) -> SSG_Vertex:
        i = 1
        while f"extra{i}" in self.vertices:
            i += 1
        new_vertex = SSG_Vertex(f"extra{i}", is_eve, is_target)
        self.vertices[f"extra{i}"] = new_vertex
        return new_vertex

    def has_action(self, action: str) -> bool:
        for transition in self.transitions.values():
            if transition.action == action:
                return True
        return False

def has_ingoing_transition(vertex: SSG_Vertex, transitions: dict([((SSG_Vertex, str),SSG_Transition)])) -> bool:
    for transition in transitions.values():
        for end_vertex in transition.end_vertices:
            if end_vertex[1] == vertex:
                return True
    return False

def is_deadlock_vertex(vertex: SSG_Vertex, transitions: dict([((SSG_Vertex, str),SSG_Transition)])) -> bool:
    for transition in transitions.values():
        if transition.start_vertex == vertex:
            return False
    return True

def read_ssg_from_file(file_name: str) -> Simple_Stochastic_Game:
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
                    ssg_vertices[current_line[0]] = SSG_Vertex(current_line[0], True, False)
                    # print(ssg_vertices[current_line[0]])
                    continue
                if (current_line[1] == "T" or current_line[1] == "t") and len(current_line) == 2:
                    if current_line[0] in ssg_vertices:
                        print_error(f"Duplicate vertex {current_line[0]}")
                    ssg_vertices[current_line[0]] = SSG_Vertex(current_line[0], True, True)
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
                    ssg_vertices[current_line[0]] = SSG_Vertex(current_line[0], False, False)
                    # print(ssg_vertices[current_line[0]])
                    continue
                if (current_line[1] == "T" or current_line[1] == "t") and len(current_line) == 2:
                    if current_line[0] in ssg_vertices:
                        print_error(f"Duplicate vertex {current_line[0]}")
                    ssg_vertices[current_line[0]] = SSG_Vertex(current_line[0], False, True)
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
                    ssg_transitions[(ssg_vertices[current_line[0]], current_line[1])] = SSG_Transition(ssg_vertices[current_line[0]], {(1.0, ssg_vertices[current_line[3]])}, current_line[1])
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
                    ssg_transitions[(ssg_vertices[current_line[0]], current_line[1])] = SSG_Transition(ssg_vertices[current_line[0]], end_vertices, current_line[1])
                    continue
                print_error(f"File does not comply with ssg specification. Line {current_line_index + 1}: {content[current_line_index]}")
            case _:
                print_error("Undefined state")
                sys.exit(1)
    return Simple_Stochastic_Game(ssg_vertices, ssg_transitions, ssg_initial_vertex)

def ssg_to_ssgspec(ssg: Simple_Stochastic_Game, file_name: str="", force: bool=False) -> str:
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

def ssg_to_smgspec(ssg: Simple_Stochastic_Game, version1: bool=False, file_name: str="", force: bool=False) -> str:
    content = "smg\n\n"

    if version1:
        ssg = copy.deepcopy(ssg)
        extra_eve_act = ""
        extra_adam_act = ""
        i = 1
        while True:
            if ssg.has_action(f"extra_eve_action{i}"):
                i += 1
            else:
                extra_eve_act = f"extra_eve_action{i}"
                break
        while True:
            if ssg.has_action(f"extra_adam_action{i}"):
                i += 1
            else:
                extra_adam_act = f"extra_adam_action{i}"
                break
        additional_ssg_transitions = dict()
        for transition in ssg.transitions.values():
            if len(transition.end_vertices) == 1:
                if transition.start_vertex.is_eve and next(iter(transition.end_vertices))[1].is_eve:
                    new_trans_vert = ssg.add_extra_vert(False)
                    additional_ssg_transitions[new_trans_vert, extra_adam_act] = SSG_Transition(new_trans_vert, {(1.0, next(iter(transition.end_vertices))[1])}, extra_adam_act)
                    additional_ssg_transitions[transition.start_vertex, transition.action] = SSG_Transition(transition.start_vertex, {(1.0, new_trans_vert)}, transition.action)
                elif not transition.start_vertex.is_eve and not next(iter(transition.end_vertices))[1].is_eve:
                    new_trans_vert = ssg.add_extra_vert(True)
                    additional_ssg_transitions[new_trans_vert, extra_eve_act] = SSG_Transition(new_trans_vert, {(1.0, next(iter(transition.end_vertices))[1])}, extra_eve_act)
                    additional_ssg_transitions[transition.start_vertex, transition.action] = SSG_Transition(transition.start_vertex, {(1.0, new_trans_vert)}, transition.action)
            else:
                if transition.start_vertex.is_eve:
                    new_trans_verts: dict([(SSG_Vertex, SSG_Vertex)]) = dict()
                    new_end_verts: set([(float, SSG_Vertex)]) = set()
                    for prob, vert in transition.end_vertices:
                        if vert.is_eve:
                            new_trans_verts[vert] = ssg.add_extra_vert(False)
                            additional_ssg_transitions[new_trans_verts[vert], extra_adam_act] = SSG_Transition(new_trans_verts[vert], {(1.0, vert)}, extra_adam_act)
                            new_end_verts.add((prob, new_trans_verts[vert]))
                        else:
                            new_end_verts.add((prob, vert))
                    additional_ssg_transitions[transition.start_vertex, transition.action] = SSG_Transition(transition.start_vertex, new_end_verts, transition.action)
                else:
                    new_trans_verts : dict([(SSG_Vertex, SSG_Vertex)]) = dict()
                    new_end_verts: set([(float, SSG_Vertex)]) = set()
                    for prob, vert in transition.end_vertices:
                        if not vert.is_eve:
                            new_trans_verts[vert] = ssg.add_extra_vert(True)
                            additional_ssg_transitions[new_trans_verts[vert], extra_eve_act] = SSG_Transition(new_trans_verts[vert], {(1.0, vert)}, extra_eve_act)
                            new_end_verts.add((prob, new_trans_verts[vert]))
                        else:
                            new_end_verts.add((prob, vert))
                    additional_ssg_transitions[transition.start_vertex, transition.action] = SSG_Transition(transition.start_vertex, new_end_verts, transition.action)
        ssg.transitions |= additional_ssg_transitions
        sanity_check_alternating_verts(ssg)
        new_vertices: dict([(SSG_Vertex, (int, int))]) = dict()
        ssg_actions: set([(bool, str)]) = set()
        new_eve_actions: dict([(str, str)]) = dict()
        new_adam_actions: dict([(str, str)]) = dict()
        new_transitions: dict([(SSG_Transition, ((int, int), str, set([(float, (int, int))])))]) = dict()
        eve_vert_count, adam_vert_count, eve_act_count, adam_act_count = 1, 1, 1, 1
        for vert in ssg.vertices.values():
            if vert.is_eve:
                new_vertices[vert] = (eve_vert_count, 0)
                eve_vert_count += 1
            else:
                new_vertices[vert] = (0, adam_vert_count)
                adam_vert_count += 1
        new_init_vertex = new_vertices[ssg.init_vertex]
        for transition in ssg.transitions.values():
            if transition.start_vertex.is_eve:
                ssg_actions.add((True, transition.action))
            else:
                ssg_actions.add((False, transition.action))
        for action in ssg_actions:
            if action[0]:
                new_eve_actions[action[1]] = f"e{eve_act_count}"
                eve_act_count += 1
            else:
                new_adam_actions[action[1]] = f"a{adam_act_count}"
                adam_act_count += 1
        for transition in ssg.transitions.values():
            if transition.start_vertex.is_eve:
                new_transitions[transition] = (
                    new_vertices[transition.start_vertex], new_eve_actions[transition.action], set())
                for prob, vert in transition.end_vertices:
                    new_transitions[transition][2].add((prob, new_vertices[vert]))
            else:
                new_transitions[transition] = (
                    new_vertices[transition.start_vertex], new_adam_actions[transition.action], set())
                for prob, vert in transition.end_vertices:
                    new_transitions[transition][2].add((prob, new_vertices[vert]))
        content += "player eve\n\tevemod"
        for act in new_eve_actions.values():
            content += f", [{act}]"
        content += "\nendplayer\n\nplayer adam\n\tadammod"
        for act in new_adam_actions.values():
            content += f", [{act}]"
        content += "\nendplayer\n\n"
        eve_mod = f"module evemod\n\teve_state : [0..{eve_vert_count-1}] init {new_init_vertex[0]} ;\n"
        adam_mod = f"module adammod\n\tadam_state : [0..{adam_vert_count-1}] init {new_init_vertex[1]} ;\n"
        for transition in new_transitions:
            if transition.start_vertex.is_eve:
                eve_mod += f"\t[{new_eve_actions[transition.action]}] (eve_state={new_transitions[transition][0][0]} & adam_state={new_transitions[transition][0][1]}) \t-> (eve_state'=0) ;\n"
                if len(transition.end_vertices) == 1:
                    adam_mod += f"\t[{new_eve_actions[transition.action]}] (eve_state={new_transitions[transition][0][0]} & adam_state={new_transitions[transition][0][1]}) \t-> (adam_state'={next(iter(new_transitions[transition][2]))[1][1]}) ;\n"
                else:
                    adam_mod += f"\t[{new_eve_actions[transition.action]}] (eve_state={new_transitions[transition][0][0]} & adam_state={new_transitions[transition][0][1]}) \t-> "
                    for prob, vert in new_transitions[transition][2]:
                        adam_mod += f"({prob}) : (adam_state'={vert[1]}) + "
                    adam_mod = adam_mod[:-3] + " ;\n"
            else:
                adam_mod += f"\t[{new_adam_actions[transition.action]}] (eve_state={new_transitions[transition][0][0]} & adam_state={new_transitions[transition][0][1]}) \t-> (adam_state'=0) ;\n"
                if len(transition.end_vertices) == 1:
                    eve_mod += f"\t[{new_adam_actions[transition.action]}] (eve_state={new_transitions[transition][0][0]} & adam_state={new_transitions[transition][0][1]}) \t-> (eve_state'={next(iter(new_transitions[transition][2]))[1][0]}) ;\n"
                else:
                    eve_mod += f"\t[{new_adam_actions[transition.action]}] (eve_state={new_transitions[transition][0][0]} & adam_state={new_transitions[transition][0][1]}) \t-> "
                    for prob, vert in new_transitions[transition][2]:
                        eve_mod += f"({prob}) : (eve_state'={vert[0]}) + "
                    eve_mod = eve_mod[:-3] + " ;\n"
        content += eve_mod + "endmodule\n\n" + adam_mod + "endmodule"
    else:
        new_vertices: dict([(SSG_Vertex, (int, int))]) = dict()
        ssg_actions: set([(bool, str)]) = set()
        new_eve_actions: dict([(str, str)]) = dict()
        new_adam_actions: dict([(str, str)]) = dict()
        new_transitions: dict([(SSG_Transition, ((int, int), str, set([(float, (int, int))])))]) = dict()
        eve_vert_count, adam_vert_count, eve_act_count, adam_act_count = 1, 1, 1, 1
        for vert in ssg.vertices.values():
            if vert.is_eve:
                new_vertices[vert] = (eve_vert_count, 0)
                eve_vert_count += 1
            else:
                new_vertices[vert] = (0, adam_vert_count)
                adam_vert_count += 1
        new_init_vertex = new_vertices[ssg.init_vertex]
        for transition in ssg.transitions.values():
            if transition.start_vertex.is_eve:
                ssg_actions.add((True, transition.action))
            else:
                ssg_actions.add((False, transition.action))
        for action in ssg_actions:
            if action[0]:
                new_eve_actions[action[1]] = f"e{eve_act_count}"
                eve_act_count += 1
            else:
                new_adam_actions[action[1]] = f"a{adam_act_count}"
                adam_act_count += 1
        for transition in ssg.transitions.values():
            if transition.start_vertex.is_eve:
                new_transitions[transition] = (
                    new_vertices[transition.start_vertex], new_eve_actions[transition.action], set())
                for prob, vert in transition.end_vertices:
                    new_transitions[transition][2].add((prob, new_vertices[vert]))
            else:
                new_transitions[transition] = (
                    new_vertices[transition.start_vertex], new_adam_actions[transition.action], set())
                for prob, vert in transition.end_vertices:
                    new_transitions[transition][2].add((prob, new_vertices[vert]))
        content += "player eve\n\tevemod"
        for act in new_eve_actions.values():
            content += f", [{act}]"
        if has_eve_probabilistic_actions(ssg):
            content += ", [ep]"
        content += "\nendplayer\n\nplayer adam\n\tadammod"
        for act in new_adam_actions.values():
            content += f", [{act}]"
        if has_adam_probabilistic_actions(ssg):
            content += ", [ap]"
        content += "\nendplayer\n\n"
        eve_mod = f"module evemod\n\teve1 : [0..{eve_vert_count-1}] init {new_init_vertex[0]} ;\n\teve2 : [0..{adam_vert_count-1}] init {new_init_vertex[1]} ;\n"
        if has_eve_probabilistic_actions(ssg):
            eve_mod += f"\trande : [0..1] init 0 ;\n"
        adam_mod = f"module adammod\n\tadam1 : [0..{eve_vert_count-1}] init {new_init_vertex[0]} ;\n\tadam2 : [0..{adam_vert_count-1}] init {new_init_vertex[1]} ;\n"
        if has_adam_probabilistic_actions(ssg):
            adam_mod += f"\tranda : [0..1] init 0 ;\n"
        rande_extra = ""
        randa_extra = ""
        if has_eve_probabilistic_actions(ssg):
            rande_extra = " & rande=0"
        if has_adam_probabilistic_actions(ssg):
            randa_extra = " & randa=0"
        for transition in new_transitions:
            if transition.start_vertex.is_eve:
                if not is_ssg_state_probabilistic(ssg, transition.start_vertex):
                    eve_mod += f"\t[{new_eve_actions[transition.action]}] (eve1={new_transitions[transition][0][0]} & eve2={new_transitions[transition][0][1]}" + rande_extra + f") \t-> (eve1'={next(iter(new_transitions[transition][2]))[1][0]}) & (eve2'={next(iter(new_transitions[transition][2]))[1][1]}) ;\n"
                    adam_mod += f"\t[{new_eve_actions[transition.action]}] (adam1={new_transitions[transition][0][0]} & adam2={new_transitions[transition][0][1]}" + rande_extra + f") \t-> (adam1'={next(iter(new_transitions[transition][2]))[1][0]}) & (adam2'={next(iter(new_transitions[transition][2]))[1][1]}) ;\n"
                else:
                    if len(transition.end_vertices) == 1:
                        eve_mod += f"\t[{new_eve_actions[transition.action]}] (eve1={new_transitions[transition][0][0]} & eve2={new_transitions[transition][0][1]} & rande=0) \t-> (eve1'={next(iter(new_transitions[transition][2]))[1][0]}) & (eve2'={next(iter(new_transitions[transition][2]))[1][1]}) & (rande'=1) ;\n"
                        adam_mod += f"\t[{new_eve_actions[transition.action]}] (adam1={new_transitions[transition][0][0]} & adam2={new_transitions[transition][0][1]} & rande=0) \t-> true ;\n"
                        adam_mod += f"\t[{new_eve_actions[transition.action]}] (adam1={new_transitions[transition][0][0]} & adam2={new_transitions[transition][0][1]} & rande=1) \t-> (adam1'= eve1) & (adam2' = eve2) ;\n"
                    else:
                        eve_mod += f"\t[{new_eve_actions[transition.action]}] (eve1={new_transitions[transition][0][0]} & eve2={new_transitions[transition][0][1]} & rande=0) \t-> "
                        for prob, vert in new_transitions[transition][2]:
                            eve_mod += f"({prob}) : (eve1'={vert[0]}) & (eve2'={vert[1]}) & (rande'=1) + "
                        eve_mod = eve_mod[:-3] + " ;\n"
                        adam_mod += f"\t[{new_eve_actions[transition.action]}] (adam1={new_transitions[transition][0][0]} & adam2={new_transitions[transition][0][1]} & rande=0) \t-> true ;\n"
            else:
                if not is_ssg_state_probabilistic(ssg, transition.start_vertex):
                    adam_mod += f"\t[{new_adam_actions[transition.action]}] (adam1={new_transitions[transition][0][0]} & adam2={new_transitions[transition][0][1]}" + randa_extra + f") \t-> (adam1'={next(iter(new_transitions[transition][2]))[1][0]}) & (adam2'={next(iter(new_transitions[transition][2]))[1][1]}) ;\n"
                    eve_mod += f"\t[{new_adam_actions[transition.action]}] (eve1={new_transitions[transition][0][0]} & eve2={new_transitions[transition][0][1]}" + rande_extra + f") \t-> (eve1'={next(iter(new_transitions[transition][2]))[1][0]}) & (eve2'={next(iter(new_transitions[transition][2]))[1][1]}) ;\n"
                else:
                    if len(transition.end_vertices) == 1:
                        adam_mod += f"\t[{new_adam_actions[transition.action]}] (adam1={new_transitions[transition][0][0]} & adam2={new_transitions[transition][0][1]} & randa=0) \t-> (adam1'={next(iter(new_transitions[transition][2]))[1][0]}) & (adam2'={next(iter(new_transitions[transition][2]))[1][1]}) & (randa'=1) ;\n"
                        eve_mod += f"\t[{new_adam_actions[transition.action]}] (eve1={new_transitions[transition][0][0]} & eve2={new_transitions[transition][0][1]} & randa=0) \t-> true ;\n"
                        eve_mod += f"\t[{new_adam_actions[transition.action]}] (eve1={new_transitions[transition][0][0]} & eve2={new_transitions[transition][0][1]} & randa=1) \t-> (eve1' = adam1) & (eve2' = adam2) ;\n"
                    else:
                        adam_mod += f"\t[{new_adam_actions[transition.action]}] (adam1={new_transitions[transition][0][0]} & adam2={new_transitions[transition][0][1]} & randa=0) \t-> "
                        for prob, vert in new_transitions[transition][2]:
                            adam_mod += f"({prob}) : (adam1'={vert[0]}) & (adam2'={vert[1]}) & (randa'=1) + "
                        adam_mod = adam_mod[:-3] + " ;\n"
                        eve_mod += f"\t[{new_adam_actions[transition.action]}] (eve1={new_transitions[transition][0][0]} & eve2={new_transitions[transition][0][1]} & randa=0) \t-> true ;\n"
        if has_eve_probabilistic_actions(ssg):
            eve_mod += f"\t[ep] (rande=1) \t\t\t\t-> (rande' = 0) ;\n"
            adam_mod += f"\t[ep] (rande=1) \t\t\t\t-> (adam1'= eve1) & (adam2' = eve2) ;\n"
        if has_adam_probabilistic_actions(ssg):
            adam_mod += f"\t[ap] (randa=1) \t\t\t\t-> (randa' = 0) ;\n"
            eve_mod += f"\t[ap] (randa=1) \t\t\t\t-> (eve1' = adam1) & (eve2' = adam2) ;\n"
        content += eve_mod + "endmodule\n\n" + adam_mod + "endmodule"
    target_vertices = set()
    for vertex in ssg.vertices.values():
        if vertex.is_target:
            target_vertices.add(new_vertices[vertex])
    if file_name:
        if not file_name.endswith(".smg"):
            print_warning("File is not an .smg file. Nothing was changed")
        elif not force and os.path.exists(file_name) and os.path.getsize(file_name) != 0:
            print_warning("File already exists. Nothing was changed")
        else:
            with open(file_name, "w", encoding="utf-8") as file:
                file.write(content)
    return content, target_vertices

def is_ssg_state_probabilistic(ssg: Simple_Stochastic_Game, state: SSG_Vertex) -> bool:
    result = False
    for transition in ssg.transitions.values():
        if transition.start_vertex == state:
            if len(transition.end_vertices) > 1:
                result = True
                break
    return result

def has_eve_probabilistic_actions(ssg: Simple_Stochastic_Game) -> bool:
    result = False
    for transition in ssg.transitions.values():
        if transition.start_vertex.is_eve and len(transition.end_vertices) > 1:
            result = True
            break
    return result

def has_adam_probabilistic_actions(ssg: Simple_Stochastic_Game) -> bool:
    result = False
    for transition in ssg.transitions.values():
        if not transition.start_vertex.is_eve and len(transition.end_vertices) > 1:
            result = True
            break
    return result

def sanity_check_alternating_verts(ssg: Simple_Stochastic_Game) -> bool:
    result = True
    for transition in ssg.transitions.values():
        if transition.start_vertex.is_eve:
            for prob, vert in transition.end_vertices:
                if vert.is_eve:
                    print_warning(f"Transition from {transition.start_vertex.name} to {vert.name} is not alternating")
                    result = False
        else:
            for prob, vert in transition.end_vertices:
                if not vert.is_eve:
                    print_warning(f"Transition from {transition.start_vertex.name} to {vert.name} is not alternating")
                    result = False