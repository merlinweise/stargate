import copy
import os.path
import time
import re
import posixpath

from stochasticreachgame import StochasticReachGame, SrgTransition, SrgVertex
from shell_commands import run_command, sh_escape, run_command_linux
from error_handling import print_warning, print_debug
from settings import GLOBAL_DEBUG, GLOBAL_IN_OUT_PATH_LINUX, PRISM_PATH, MAX_ITERS, PRISM_EPSILON, PRISM_SOLVING_ALGORITHM, GLOBAL_IN_OUT_PATH, IS_OS_LINUX, GLOBAL_IN_OUT_PATH_WINDOWS


def srg_to_smgspec(srg: StochasticReachGame, version1: bool = False, debug: bool = GLOBAL_DEBUG, print_correspondingvertices: bool = False) -> str:
    if debug:
        start_time = time.perf_counter()
    content = "smg\n\n"
    if version1:
        srg = copy.deepcopy(srg)
        i = 1
        while True:
            if srg.has_action(f"extra_eve_action{i}"):
                i += 1
            else:
                extra_eve_act = f"extra_eve_action{i}"
                break
        i = 1
        while True:
            if srg.has_action(f"extra_adam_action{i}"):
                i += 1
            else:
                extra_adam_act = f"extra_adam_action{i}"
                break
        additional_srg_transitions = dict()
        for transition in srg.transitions.values():
            if len(transition.end_vertices) == 1:
                if transition.start_vertex == next(iter(transition.end_vertices))[1]:
                    continue
                elif transition.start_vertex.is_eve and next(iter(transition.end_vertices))[1].is_eve:
                    new_trans_vert = srg.add_extra_vert(False)
                    additional_srg_transitions[new_trans_vert, extra_adam_act] = SrgTransition(new_trans_vert, {(1.0, next(iter(transition.end_vertices))[1])}, extra_adam_act)
                    additional_srg_transitions[transition.start_vertex, transition.action] = (SrgTransition(transition.start_vertex, {(1.0, new_trans_vert)}, transition.action))
                elif not transition.start_vertex.is_eve and not next(iter(transition.end_vertices))[1].is_eve:
                    new_trans_vert = srg.add_extra_vert(True)
                    additional_srg_transitions[new_trans_vert, extra_eve_act] = SrgTransition(new_trans_vert, {(1.0, next(iter(transition.end_vertices))[1])}, extra_eve_act)
                    additional_srg_transitions[transition.start_vertex, transition.action] = (SrgTransition(transition.start_vertex, {(1.0, new_trans_vert)}, transition.action))
            else:
                if transition.start_vertex.is_eve:
                    new_trans_verts: dict[SrgVertex, SrgVertex] = dict()
                    new_end_verts: set[tuple[float, SrgVertex]] = set()
                    for prob, vert in transition.end_vertices:
                        if vert.is_eve:
                            new_trans_verts[vert] = srg.add_extra_vert(False)
                            additional_srg_transitions[new_trans_verts[vert], extra_adam_act] = (SrgTransition(new_trans_verts[vert], {(1.0, vert)}, extra_adam_act))
                            new_end_verts.add((prob, new_trans_verts[vert]))
                        else:
                            new_end_verts.add((prob, vert))
                    additional_srg_transitions[transition.start_vertex, transition.action] = (SrgTransition(transition.start_vertex, new_end_verts, transition.action))
                else:
                    new_trans_verts: dict[SrgVertex, SrgVertex] = dict()
                    new_end_verts: set[tuple[float, SrgVertex]] = set()
                    for prob, vert in transition.end_vertices:
                        if not vert.is_eve:
                            new_trans_verts[vert] = srg.add_extra_vert(True)
                            additional_srg_transitions[new_trans_verts[vert], extra_eve_act] = (SrgTransition(new_trans_verts[vert], {(1.0, vert)}, extra_eve_act))
                            new_end_verts.add((prob, new_trans_verts[vert]))
                        else:
                            new_end_verts.add((prob, vert))
                    additional_srg_transitions[transition.start_vertex, transition.action] = (SrgTransition(transition.start_vertex, new_end_verts, transition.action))
        srg.transitions |= additional_srg_transitions
        if not sanity_check_alternating_vertices(srg):
            print_warning("The SRG is not alternating. The generated SMG may not be correct.")
        new_vertices: dict[SrgVertex, tuple[int, int]] = dict()
        srg_eve_actions: set[str] = set()
        srg_adam_actions: set[str] = set()
        new_eve_actions: dict[str, str] = dict()
        new_adam_actions: dict[str, str] = dict()
        new_transitions: dict[SrgTransition, tuple[tuple[int, int], str, set[tuple[float, tuple[int, int]]]]] = dict()
        eve_vert_count, adam_vert_count, eve_act_count, adam_act_count = 1, 1, 1, 1
        for vert in srg.vertices.values():
            if vert.is_eve:
                new_vertices[vert] = (eve_vert_count, 0)
                eve_vert_count += 1
            else:
                new_vertices[vert] = (0, adam_vert_count)
                adam_vert_count += 1

        if print_correspondingvertices:
            print("Corresponding vertices:")
            for vert in srg.vertices.values():
                print(f"{vert.name} -> {new_vertices[vert]}")
        new_init_vertex = new_vertices[srg.init_vertex]
        for transition in srg.transitions.values():
            if transition.start_vertex.is_eve:
                srg_eve_actions.add(transition.action)
            else:
                srg_adam_actions.add(transition.action)

        for action in srg_eve_actions:
            new_eve_actions[action] = f"e{eve_act_count}"
            eve_act_count += 1

        for action in srg_adam_actions:
            new_adam_actions[action] = f"a{adam_act_count}"
            adam_act_count += 1
        for transition in srg.transitions.values():
            if transition.start_vertex.is_eve:
                new_transitions[transition] = (new_vertices[transition.start_vertex], new_eve_actions[transition.action], set())
                for prob, vert in transition.end_vertices:
                    new_transitions[transition][2].add((prob, new_vertices[vert]))
            else:
                new_transitions[transition] = (new_vertices[transition.start_vertex], new_adam_actions[transition.action], set())
                for prob, vert in transition.end_vertices:
                    new_transitions[transition][2].add((prob, new_vertices[vert]))
        content += "player eve\n\tevemod"
        for act in new_eve_actions.values():
            content += f", [{act}]"
        content += "\nendplayer\n\nplayer adam\n\tadammod"
        for act in new_adam_actions.values():
            content += f", [{act}]"
        content += "\nendplayer\n\n"
        eve_mod = f"module evemod\n\tes : [0..{eve_vert_count-1}] init {new_init_vertex[0]} ;\n"
        adam_mod = f"module adammod\n\tas : [0..{adam_vert_count-1}] init {new_init_vertex[1]} ;\n"
        for transition in new_transitions:
            if transition.start_vertex.is_eve:
                if len(transition.end_vertices) == 1:
                    if transition.start_vertex == next(iter(transition.end_vertices))[1]:
                        adam_mod += f"\t[{new_eve_actions[transition.action]}] (es={new_transitions[transition][0][0]} & as={new_transitions[transition][0][1]}) \t-> true ;\n"
                        eve_mod += f"\t[{new_eve_actions[transition.action]}] (es={new_transitions[transition][0][0]} & as={new_transitions[transition][0][1]}) \t-> true ;\n"
                        continue
                    else:
                        adam_mod += f"\t[{new_eve_actions[transition.action]}] (es={new_transitions[transition][0][0]} & as={new_transitions[transition][0][1]}) \t-> (as'={next(iter(new_transitions[transition][2]))[1][1]}) ;\n"
                else:
                    adam_mod += f"\t[{new_eve_actions[transition.action]}] (es={new_transitions[transition][0][0]} & as={new_transitions[transition][0][1]}) \t-> "
                    for prob, vert in new_transitions[transition][2]:
                        adam_mod += f"({prob}) : (as'={vert[1]}) + "
                    adam_mod = adam_mod[:-3] + " ;\n"
                eve_mod += f"\t[{new_eve_actions[transition.action]}] (es={new_transitions[transition][0][0]} & as={new_transitions[transition][0][1]}) \t-> (es'=0) ;\n"
            else:
                if len(transition.end_vertices) == 1:
                    if transition.start_vertex == next(iter(transition.end_vertices))[1]:
                        eve_mod += f"\t[{new_adam_actions[transition.action]}] (es={new_transitions[transition][0][0]} & as={new_transitions[transition][0][1]}) \t-> true ;\n"
                        adam_mod += f"\t[{new_adam_actions[transition.action]}] (es={new_transitions[transition][0][0]} & as={new_transitions[transition][0][1]}) \t-> true ;\n"
                        continue
                    else:
                        eve_mod += f"\t[{new_adam_actions[transition.action]}] (es={new_transitions[transition][0][0]} & as={new_transitions[transition][0][1]}) \t-> (es'={next(iter(new_transitions[transition][2]))[1][0]}) ;\n"
                else:
                    eve_mod += f"\t[{new_adam_actions[transition.action]}] (es={new_transitions[transition][0][0]} & as={new_transitions[transition][0][1]}) \t-> "
                    for prob, vert in new_transitions[transition][2]:
                        eve_mod += f"({prob}) : (es'={vert[0]}) + "
                    eve_mod = eve_mod[:-3] + " ;\n"
                adam_mod += f"\t[{new_adam_actions[transition.action]}] (es={new_transitions[transition][0][0]} & as={new_transitions[transition][0][1]}) \t-> (as'=0) ;\n"
        content += eve_mod + "endmodule\n\n" + adam_mod + "endmodule"
    else:
        new_vertices: dict[SrgVertex, tuple[int, int]] = dict()
        srg_eve_actions: set[str] = set()
        srg_adam_actions: set[str] = set()
        new_eve_actions: dict[str, str] = dict()
        new_adam_actions: dict[str, str] = dict()
        new_transitions: dict[SrgTransition, tuple[tuple[int, int], str, set[tuple[float, tuple[int, int]]]]] = dict()
        eve_vert_count, adam_vert_count, eve_act_count, adam_act_count = 1, 1, 1, 1
        for vert in srg.vertices.values():
            if vert.is_eve:
                new_vertices[vert] = (eve_vert_count, 0)
                eve_vert_count += 1
            else:
                new_vertices[vert] = (0, adam_vert_count)
                adam_vert_count += 1
        if print_correspondingvertices:
            print("Corresponding vertices:")
            for vert in srg.vertices.values():
                print(f"{vert.name} -> {new_vertices[vert]}")
        new_init_vertex = new_vertices[srg.init_vertex]
        for transition in srg.transitions.values():
            if transition.start_vertex.is_eve:
                srg_eve_actions.add(transition.action)
            else:
                srg_adam_actions.add(transition.action)
        for action in srg_eve_actions:
            new_eve_actions[action] = f"e{eve_act_count}"
            eve_act_count += 1
        for action in srg_adam_actions:
            new_adam_actions[action] = f"a{adam_act_count}"
            adam_act_count += 1
        for transition in srg.transitions.values():
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
        if has_eve_probabilistic_actions(srg):
            content += ", [ep]"
        content += "\nendplayer\n\nplayer adam\n\tadammod"
        for act in new_adam_actions.values():
            content += f", [{act}]"
        if has_adam_probabilistic_actions(srg):
            content += ", [ap]"
        content += "\nendplayer\n\n"
        eve_mod = f"module evemod\n\te1 : [0..{eve_vert_count-1}] init {new_init_vertex[0]} ;\n\te2 : [0..{adam_vert_count-1}] init {new_init_vertex[1]} ;\n"
        if has_eve_probabilistic_actions(srg):
            eve_mod += f"\tre : [0..1] init 0 ;\n"
        adam_mod = f"module adammod\n\ta1 : [0..{eve_vert_count-1}] init {new_init_vertex[0]} ;\n\ta2 : [0..{adam_vert_count-1}] init {new_init_vertex[1]} ;\n"
        if has_adam_probabilistic_actions(srg):
            adam_mod += f"\tra : [0..1] init 0 ;\n"
        rande_extra = ""
        randa_extra = ""
        if has_eve_probabilistic_actions(srg):
            rande_extra = " & re=0"
        if has_adam_probabilistic_actions(srg):
            randa_extra = " & ra=0"
        for transition in new_transitions:
            if transition.start_vertex.is_eve:
                if not is_srg_vertex_probabilistic(srg, transition.start_vertex):
                    eve_mod += (f"\t[{new_eve_actions[transition.action]}] (e1={new_transitions[transition][0][0]} & e2={new_transitions[transition][0][1]}" + rande_extra + f") \t-> (e1'={next(iter(new_transitions[transition][2]))[1][0]}) & (e2'={next(iter(new_transitions[transition][2]))[1][1]}) ;\n")
                    adam_mod += (f"\t[{new_eve_actions[transition.action]}] (a1={new_transitions[transition][0][0]} & a2={new_transitions[transition][0][1]}" + rande_extra + f") \t-> (a1'={next(iter(new_transitions[transition][2]))[1][0]}) & (a2'={next(iter(new_transitions[transition][2]))[1][1]}) ;\n")
                else:
                    if len(transition.end_vertices) == 1:
                        eve_mod += f"\t[{new_eve_actions[transition.action]}] (e1={new_transitions[transition][0][0]} & e2={new_transitions[transition][0][1]} & re=0) \t-> (e1'={next(iter(new_transitions[transition][2]))[1][0]}) & (e2'={next(iter(new_transitions[transition][2]))[1][1]}) & (re'=1) ;\n"
                        adam_mod += f"\t[{new_eve_actions[transition.action]}] (a1={new_transitions[transition][0][0]} & a2={new_transitions[transition][0][1]} & re=0) \t-> true ;\n"
                        adam_mod += f"\t[{new_eve_actions[transition.action]}] (a1={new_transitions[transition][0][0]} & a2={new_transitions[transition][0][1]} & re=1) \t-> (a1'= e1) & (a2' = e2) ;\n"
                    else:
                        eve_mod += f"\t[{new_eve_actions[transition.action]}] (e1={new_transitions[transition][0][0]} & e2={new_transitions[transition][0][1]} & re=0) \t-> "
                        for prob, vert in new_transitions[transition][2]:
                            eve_mod += f"({prob}) : (e1'={vert[0]}) & (e2'={vert[1]}) & (re'=1) + "
                        eve_mod = eve_mod[:-3] + " ;\n"
                        adam_mod += f"\t[{new_eve_actions[transition.action]}] (a1={new_transitions[transition][0][0]} & a2={new_transitions[transition][0][1]} & re=0) \t-> true ;\n"
            else:
                if not is_srg_vertex_probabilistic(srg, transition.start_vertex):
                    adam_mod += (f"\t[{new_adam_actions[transition.action]}] (a1={new_transitions[transition][0][0]} & a2={new_transitions[transition][0][1]}" + randa_extra + f") \t-> (a1'={next(iter(new_transitions[transition][2]))[1][0]}) & (a2'={next(iter(new_transitions[transition][2]))[1][1]}) ;\n")
                    eve_mod += (f"\t[{new_adam_actions[transition.action]}] (e1={new_transitions[transition][0][0]} & e2={new_transitions[transition][0][1]}" + rande_extra + f") \t-> (e1'={next(iter(new_transitions[transition][2]))[1][0]}) & (e2'={next(iter(new_transitions[transition][2]))[1][1]}) ;\n")
                else:
                    if len(transition.end_vertices) == 1:
                        adam_mod += f"\t[{new_adam_actions[transition.action]}] (a1={new_transitions[transition][0][0]} & a2={new_transitions[transition][0][1]} & ra=0) \t-> (a1'={next(iter(new_transitions[transition][2]))[1][0]}) & (a2'={next(iter(new_transitions[transition][2]))[1][1]}) & (ra'=1) ;\n"
                        eve_mod += f"\t[{new_adam_actions[transition.action]}] (e1={new_transitions[transition][0][0]} & e2={new_transitions[transition][0][1]} & ra=0) \t-> true ;\n"
                        eve_mod += f"\t[{new_adam_actions[transition.action]}] (e1={new_transitions[transition][0][0]} & e2={new_transitions[transition][0][1]} & ra=1) \t-> (e1' = a1) & (e2' = a2) ;\n"
                    else:
                        adam_mod += f"\t[{new_adam_actions[transition.action]}] (a1={new_transitions[transition][0][0]} & a2={new_transitions[transition][0][1]} & ra=0) \t-> "
                        for prob, vert in new_transitions[transition][2]:
                            adam_mod += f"({prob}) : (a1'={vert[0]}) & (a2'={vert[1]}) & (ra'=1) + "
                        adam_mod = adam_mod[:-3] + " ;\n"
                        eve_mod += f"\t[{new_adam_actions[transition.action]}] (e1={new_transitions[transition][0][0]} & e2={new_transitions[transition][0][1]} & ra=0) \t-> true ;\n"
        if has_eve_probabilistic_actions(srg):
            eve_mod += f"\t[ep] (re=1) \t\t\t\t-> (re' = 0) ;\n"
            adam_mod += f"\t[ep] (re=1) \t\t\t\t-> (a1'= e1) & (a2' = e2) ;\n"
        if has_adam_probabilistic_actions(srg):
            adam_mod += f"\t[ap] (ra=1) \t\t\t\t-> (ra' = 0) ;\n"
            eve_mod += f"\t[ap] (ra=1) \t\t\t\t-> (e1' = a1) & (e2' = a2) ;\n"
        content += eve_mod + "endmodule\n\n" + adam_mod + "endmodule"
    content += "\n\nlabel \"target\" = ("
    for vertex in srg.vertices.values():
        if vertex.is_target:
            if version1:
                content += f"(es={new_vertices[vertex][0]}) & (as={new_vertices[vertex][1]}) | "
            else:
                content += f"(e1={new_vertices[vertex][0]}) & (e2={new_vertices[vertex][1]}) | "
    if content[-1:] == "(":
        content = content[:-1] + "false;"
    else:
        content = content[:-3] + ");"
    if debug:
        print_debug(f"SMG specification created in {(time.perf_counter() - start_time):.6f} seconds with version {1 if version1 else 2}")
    return content


def is_srg_vertex_probabilistic(srg: StochasticReachGame, state: SrgVertex) -> bool:
    """
    Checks if the given state in the StochasticReachGame has probabilistic transitions.
    This is used to determine if the state has multiple end vertices with different probabilities.
    Needed for version 2 of the SMG specification.
    :param srg: The StochasticReachGame to check.
    :type srg: StochasticReachGame
    :param state:
    :return:
    """
    for transition in srg.transitions.values():
        if transition.start_vertex == state:
            if len(transition.end_vertices) > 1:
                return True
                break
    return False


def has_eve_probabilistic_actions(srg: StochasticReachGame) -> bool:
    """
    Checks if the StochasticReachGame has any probabilistic actions for Eve.
    Needed for version 2 of the SMG specification.
    :param srg: The StochasticReachGame to check.
    :type srg: StochasticReachGame
    :return: True if Eve has probabilistic actions, False otherwise.
    :rtype: bool
    """
    for transition in srg.transitions.values():
        if transition.start_vertex.is_eve and len(transition.end_vertices) > 1:
            return True
            break
    return False


def has_adam_probabilistic_actions(srg: StochasticReachGame) -> bool:
    """
    Checks if the StochasticReachGame has any probabilistic actions for Adam.
    Needed for version 2 of the SMG specification.
    :param srg: The StochasticReachGame to check.
    :type srg: StochasticReachGame
    :return: True if Adam has probabilistic actions, False otherwise.
    :rtype: bool
    """
    for transition in srg.transitions.values():
        if not transition.start_vertex.is_eve and len(transition.end_vertices) > 1:
            return True
            break
    return False


def sanity_check_alternating_vertices(srg: StochasticReachGame) -> bool:
    """
    Checks if the SRG is alternating, meaning that transitions from eve vertices lead to adam vertices and vice versa.
    :param srg: The StochasticReachGame to check.
    :type srg: StochasticReachGame
    :return: True if the SRG is alternating, False otherwise.
    :rtype: bool
    """
    for transition in srg.transitions.values():
        if len(transition.end_vertices) == 1 and transition.start_vertex == next(iter(transition.end_vertices))[1]:
            continue
        if transition.start_vertex.is_eve:
            for prob, vert in transition.end_vertices:
                if vert.is_eve:
                    print_warning(f"Transition from {transition.start_vertex.name} to {vert.name} is neither alternating nor a self-loop.")
                    return False
        else:
            for prob, vert in transition.end_vertices:
                if not vert.is_eve:
                    print_warning(f"Transition from {transition.start_vertex.name} to {vert.name} is neither alternating nor a self-loop.")
                    return False
    return True


def check_property(smg_file, property_string, use_global_path: bool = False, debug: bool = GLOBAL_DEBUG) -> float:
    if debug:
        start_time = time.perf_counter()
    if use_global_path:
        smg_file = posixpath.join(GLOBAL_IN_OUT_PATH_LINUX, smg_file)
    command = f"{sh_escape(PRISM_PATH)} {sh_escape(smg_file)} -pf {sh_escape(property_string)} -maxiters {str(MAX_ITERS)} -epsilon {str(PRISM_EPSILON)} {sh_escape(PRISM_SOLVING_ALGORITHM)}"
    result = run_command_linux(command=command, use_shell=True, debug=debug)
    output = result.stdout
    match = re.search(r'Result:\s*(\d\.\d+(E-\d+)?)', output)
    if match:
        probability = float(match.group(1))
        if debug:
            print_debug(f"Property {property_string} checked in {(time.perf_counter() - start_time):.6f} seconds")
        return probability
    else:
        if debug:
            print_debug(f"Property {property_string} check failed after {(time.perf_counter() - start_time):.6f} seconds")
        return -1.0


def check_target_reachability(smg_file: str, print_probabilities: bool = False, debug: bool = GLOBAL_DEBUG, use_global_path: bool = False) -> str:
    if debug:
        start_time = time.perf_counter()
    if use_global_path:
        smg_file = posixpath.join(GLOBAL_IN_OUT_PATH_LINUX, smg_file)
    if debug:
        pre_prob1_time = time.perf_counter()
    result1 = check_property(smg_file=smg_file, property_string=f"<<eve>> Pmin=? [F \"target\"]", debug=debug)
    if debug:
        print_debug(f"First prob checking time: {(time.perf_counter() - pre_prob1_time):.6f}")
    if result1 == -1.0:
        result = "Could not check minimum probability of reaching a target for eve.\n"
    else:
        result = f"Minimum probability of reaching a target state for eve: {str(result1)}\n"
    if debug:
        pre_prob2_time = time.perf_counter()
    result2 = check_property(smg_file=smg_file, property_string=f"<<eve>> Pmax=? [F \"target\"]", debug=debug)
    if debug:
        print_debug(f"Second prob checking time: {(time.perf_counter() - pre_prob2_time):.6f}")
    if result2 == -1.0:
        result += "Could not check maximum probability of reaching a target for eve.\n"
    else:
        result += f"Maximum probability of reaching a target state for eve: {str(result2)}"
    if print_probabilities:
        print(result)
    if debug:
        print_debug(f"Target reachability check completed in {(time.perf_counter() - start_time):.6f} seconds")
    return result


def save_smg_file(content: str, file_name: str = "", force: bool = False, debug: bool = GLOBAL_DEBUG, use_global_path: bool = False):
    if debug:
        start_time = time.perf_counter()
    if not file_name:
        file_name = "out.smg"
    if use_global_path:
        file_name = os.path.join(GLOBAL_IN_OUT_PATH, file_name)
    if not file_name.endswith(".smg"):
        print_warning(f"File {file_name} is not an .smg file. Nothing was changed")
    elif not force and os.path.exists(file_name) and os.path.getsize(file_name) > 0:
        print_warning(f"File {file_name} already exists. Nothing was changed")
    else:
        try:
            with open(file_name, "w") as file:
                file.write(content)
        except Exception as e:
            print_warning(f"Could not save SMG file {file_name}. Error: {str(e)}")
            return
    if debug:
        print_debug(f"SMG file {file_name} created in {(time.perf_counter() - start_time):.6f} seconds")


def create_dot_file(smg_file: str, dot_file: str = "", force: bool = False, debug: bool = GLOBAL_DEBUG, use_global_path: bool = False):
    if debug:
        start_time = time.perf_counter()
    if use_global_path:
        if not IS_OS_LINUX:
            smg_file_win = os.path.join(GLOBAL_IN_OUT_PATH_WINDOWS, smg_file)
        smg_file = posixpath.join(GLOBAL_IN_OUT_PATH_LINUX, smg_file)
    if not dot_file:
        if not IS_OS_LINUX:
            dot_file_win = smg_file_win.replace(".smg", ".dot")
        dot_file = smg_file.replace(".smg", ".dot")
    if use_global_path:
        if not IS_OS_LINUX:
            dot_file_win = os.path.join(GLOBAL_IN_OUT_PATH_WINDOWS, dot_file_win)
        dot_file = posixpath.join(GLOBAL_IN_OUT_PATH_LINUX, dot_file)
    if not IS_OS_LINUX:
        if not force and os.path.exists(dot_file_win) and os.path.getsize(dot_file_win) > 0:
            print_warning("DOT file already exists. Nothing was changed")
        else:
            run_command_linux(f"{sh_escape(PRISM_PATH)} {sh_escape(smg_file)} -exporttransdotstates {sh_escape(dot_file)}", use_shell=True, debug=debug)
    else:
        if not force and os.path.exists(dot_file) and os.path.getsize(dot_file) > 0:
            print_warning("DOT file already exists. Nothing was changed")
        else:
            run_command_linux(f"{sh_escape(PRISM_PATH)} {sh_escape(smg_file)} -exporttransdotstates {sh_escape(dot_file)}", use_shell=True, debug=debug)
    if debug:
        print_debug(f"DOT file {dot_file} created in {(time.perf_counter() - start_time):.6f} seconds")


def create_png_file(dot_file: str, png_file: str = "", open_png: bool = False, force: bool = False, debug: bool = GLOBAL_DEBUG, use_global_path: bool = False):
    if debug:
        start_time = time.perf_counter()
    if use_global_path:
        if not IS_OS_LINUX:
            dot_file_win = os.path.join(GLOBAL_IN_OUT_PATH_WINDOWS, dot_file)
        dot_file = posixpath.join(GLOBAL_IN_OUT_PATH_LINUX, dot_file)
    if not png_file:
        if not IS_OS_LINUX:
            png_file_win = dot_file_win.replace(".dot", ".png")
        png_file = dot_file.replace(".dot", ".png")
    if use_global_path:
        if not IS_OS_LINUX:
            png_file_win = os.path.join(GLOBAL_IN_OUT_PATH_WINDOWS, png_file_win)
        png_file = posixpath.join(GLOBAL_IN_OUT_PATH_LINUX, png_file)
    if not IS_OS_LINUX:
        if not force and os.path.exists(png_file_win) and os.path.getsize(png_file_win) > 0:
            print_warning("PNG file already exists. Nothing was changed")
        else:
            run_command("dot -Tpng " + dot_file_win + " -o " + png_file_win, use_shell=True, debug=debug)
    else:
        if not force and os.path.exists(png_file) and os.path.getsize(png_file) > 0:
            print_warning("PNG file already exists. Nothing was changed")
        else:
            run_command(f"dot -Tpng {sh_escape(dot_file)} -o {sh_escape(png_file)}", use_shell=True, debug=debug)
    if open_png:
        if IS_OS_LINUX:
            run_command(f"xdg-open {png_file}", use_shell=True, debug=debug)
        else:
            run_command(f"start {png_file_win}", use_shell=True, debug=debug)
    if debug:
        print_debug(f"PNG file {dot_file} created in {(time.perf_counter() - start_time):.6f} seconds")


# create_dot_file("raphael2.smg", force=True, use_global_path=True)
# create_png_file("raphael2.dot", force=True, use_global_path=True, open_png=True)
