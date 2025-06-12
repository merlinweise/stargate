import subprocess

from error_handling import print_error, print_debug
from settings import GLOBAL_DEBUG, IS_OS_LINUX, IS_WSL_INSTALLED


def sh_escape(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def run_command(command: str | list[str], use_shell: bool = True, debug: bool = GLOBAL_DEBUG):
    if isinstance(command, str) and not use_shell:
        command = command.split(' ')
        if debug:
            print_debug("Using shell=False with a string command, which may lead to unexpected behavior. Consider using a list command instead.")
    if isinstance(command, list) and use_shell:
        command = ' '.join(arg for arg in command)
        if debug:
            print_debug("Using shell=True with a string command, which may lead to unexpected behavior. Consider using a list command instead.")
    try:
        result = subprocess.run(command, shell=use_shell, capture_output=True, text=True, check=True)
        if debug:
            print(result.stdout)
        return result

    except subprocess.CalledProcessError as e:
        print_error(f"Command {command} failed with error: {e.stderr}")
        return None


def run_command_linux(command: str | list[str], use_shell: bool = True, debug: bool = GLOBAL_DEBUG):
    try:
        if use_shell:
            if IS_OS_LINUX:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            elif IS_WSL_INSTALLED:
                result = subprocess.run(["wsl", "bash", "-c", command], capture_output=True, text=True, check=True)
            else:
                print_error(
                    "Error: The current OS is not Linux nor is WSL installed. Please run this script on a Linux system or install WSL.")
                return None
        else:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)

        if debug:
            print(result.stdout)
        return result

    except subprocess.CalledProcessError as e:
        print_error(f"Command {command} failed with error: {e.stderr}")
        return None
