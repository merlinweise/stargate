import subprocess
from error_handling import print_error
from settings import GLOBAL_DEBUG


def run_command(command_list, use_shell=False, debug=GLOBAL_DEBUG):
    try:
        if use_shell:
            command = " ".join(f'"{arg}"' if " " in arg else arg for arg in command_list)
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        else:
            result = subprocess.run(command_list, shell=False, capture_output=True, text=True, check=True)
        if debug:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError:
        # if debug:
        print_error(f"Command {' '.join(command_list)} failed with error: {result.stderr}")
        return None
