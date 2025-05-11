import simple_parity_game
import simple_stochastic_game
import spg_to_ssg_reduction
import re
import subprocess
import platform
import os
import time
from error_handling import print_warning, print_error


def run_command(command_list, use_shell=False, debug=False):
    try:
        if use_shell:
            command = " ".join(f'"{arg}"' if " " in arg else arg for arg in command_list)
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        else:
            result = subprocess.run(command_list, shell=False, capture_output=True, text=True, check=True)
        #if debug:
            #print(result.stdout)
    except subprocess.CalledProcessError as e:
        print_error(f"Could not execute command {' '.join(command_list)}.")


def check_property(smg_file, property_string) -> float:
    command = ["prism", smg_file, "-pf", property_string]
    result = subprocess.run(command, capture_output=True, text=True, shell=True)

    output = result.stdout
    #print("PRISM output:\n", output)

    match = re.search(r'Result:\s*([\d]\.\d+(E\-\d+)?)', output)
    if match:
        probability = float(match.group(1))
        return probability
    else:
        return -1.0


def convert_ssg_to_png(ssg_file, smg_file="", dot_file="", png_file="", ssg_to_smg_version1=True, force=False, create_png=False, open_png=True, print_target_probabilities=True, debug=False):
    if debug:
        start_time = time.time()
    try:
        with open("in_out_paths.txt", "r", encoding="utf-8") as file:
            paths = file.readlines()
    except FileNotFoundError:
        print_error(f"File in_out_paths.txt not found.")
    except Exception as e:
        print_error(f"Could not read the file: {e}")
    in_path = paths[0].replace("\n","").strip()
    out_path = paths[1].replace("\n","").strip()
    if not smg_file:
        smg_file = os.path.join(out_path, ssg_file.replace('.ssg', '.smg'))
    if create_png:
        if not dot_file:
            dot_file = os.path.join(out_path, ssg_file.replace('.ssg', '.dot'))
        if not png_file:
            png_file = os.path.join(out_path, ssg_file.replace('.ssg', '.png'))
    ssg_file = os.path.join(in_path, ssg_file)
    ssg = simple_stochastic_game.read_ssg_from_file(ssg_file)
    if debug:
        pre_smg_spec_time = time.time()
    smg, target_vertices = simple_stochastic_game.ssg_to_smgspec(ssg=ssg, version1=ssg_to_smg_version1, file_name=smg_file, force=force)
    if debug:
        print(f"SMG spec created {(time.time() - pre_smg_spec_time):.6f}")
    if create_png:
        if debug:
            pre_dot_time = time.time()
        run_command(["prism", smg_file, "-exporttransdotstates", f"{dot_file}"], use_shell=True, debug=debug)
        if debug:
            print(f"DOT-file created {(time.time() - pre_dot_time):.6f}")
            pre_png_time = time.time()
        run_command(["dot", "-Tpng", dot_file, "-o", png_file], use_shell=True, debug=debug)
        if debug:
            print(f"PNG-file created {(time.time() - pre_png_time):.6f}")
    if print_target_probabilities:
        target_property = "[ F "
        if ssg_to_smg_version1:
            for vertex in target_vertices:
                target_property += f"( eve_state={vertex[0]} & adam_state={vertex[1]} ) | "
        else:
            for vertex in target_vertices:
                target_property += f"( eve1={vertex[0]} & eve2={vertex[1]}) | "
        target_property = target_property[:-3] + " ]"
        if debug:
            pre_first_prob_check_time = time.time()
        result = check_property(smg_file=smg_file, property_string=f"<<eve>> Pmin=? {target_property}")
        if debug:
            print(f"First prob checking time: {(time.time() - pre_first_prob_check_time):.6f}")
        print(f"Min probability for eve of reaching target vertices: {result}")
        if debug:
            pre_second_prob_check_time = time.time()
        result = check_property(smg_file=smg_file, property_string=f"<<eve>> Pmax=? {target_property}")
        if debug:
            print(f"Second prob checking time: {(time.time() - pre_second_prob_check_time):.6f}")
        print(f"Max probability for eve of reaching target vertices: {result}")
    if create_png and open_png:
        if platform.system() == "Windows":
            run_command(["start", png_file], use_shell=True, debug=debug)
        elif platform.system() == "Linux":
            run_command(["xdg-open", png_file], use_shell=True, debug=debug)
    if debug:
        print(f"Elapsed time: {(time.time() - start_time):.6f} seconds")



convert_ssg_to_png("raphael.ssg", force=True, ssg_to_smg_version1=False, debug=True, create_png=True, open_png=True)
#spg=simple_parity_game.read_spg_from_file("C:\\Uni_Zeug\\6.Semester\\Bachelorarbeit\\PRISMgames_testing\\program_input\\elbeck.spg")

#print(spg_to_ssg_reduction.compute_alphas_for_spg(spg=spg))