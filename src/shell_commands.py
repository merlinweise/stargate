import subprocess

from error_handling import print_error, print_debug, print_warning
from settings import GLOBAL_DEBUG, IS_OS_LINUX, IS_WSL_INSTALLED


def sh_escape(s: str) -> str:
    """
    Escapes a string for use in a shell command by wrapping it in single quotes and escaping any single quotes within the string.
    :param s: String to escape
    :type s: str
    :return: Escaped string suitable for shell commands
    :rtype: str
    """
    return "'" + s.replace("'", "'\\''") + "'"


def run_command(command: str | list[str], use_shell: bool = True, debug: bool = GLOBAL_DEBUG) -> subprocess.CompletedProcess | None:
    """
    Runs a shell command and returns the result.
    :param command: Command to run, can be a string or a list of strings
    :type command: str | list[str]
    :param use_shell: Whether to use the shell to execute the command, default is True
    :type use_shell: bool
    :param debug: Whether to print debug information, default is GLOBAL_DEBUG
    :type debug: bool
    :return: Result of the command execution, or None if the command failed
    :rtype: subprocess.CompletedProcess | None
    """
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


def run_command_linux(command: str | list[str], use_shell: bool = True, debug: bool = GLOBAL_DEBUG) -> subprocess.CompletedProcess | None:
    """
    Runs a shell command on a Linux system or WSL and returns the result.
    :param command: Command to run, can be a string or a list of strings
    :type command: str | list[str]
    :param use_shell: Whether to use the shell to execute the command, default is True
    :type use_shell: bool
    :param debug: Whether to print debug information, default is GLOBAL_DEBUG
    :type debug: bool
    :return: Result of the command execution, or None if the command failed
    :rtype: subprocess.CompletedProcess | None
    """
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
        if len(e.stderr) > 0:
            print_warning(f"Command {command} failed with error: {e.stderr}")
        else:
            print_warning(f"Command {command} failed with error: {e.stdout}")
        return None
