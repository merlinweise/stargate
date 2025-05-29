import subprocess
from error_handling import print_error
from settings import GLOBAL_DEBUG, IS_OS_LINUX, IS_WSL_INSTALLED, GLOBAL_IN_OUT_PATH


def path_exists(path):
    if IS_OS_LINUX:
        # If running on Linux, we can directly check the path
        return subprocess.run(["test", "-e", path], capture_output=True).returncode == 0
    elif IS_WSL_INSTALLED:
        # If WSL is installed, we can use the wsl command to check the path
        return subprocess.run(["wsl", "test", "-e", path], capture_output=True).returncode == 0
    else:
        # If neither condition is met, we cannot check the path
        print_error("Error: The current OS is not Linux nor is WSL installed. Please run this script on a Linux system or install WSL.")
        return False


def get_linux_path_size(path):
    """
    Get the size of a file or directory in WSL (Linux) using the `stat` command.
    :param path:
    :return:
    """
    if IS_OS_LINUX:
        # If running on Linux, we can directly use the stat command
        result = subprocess.run(["stat", "-c", "%s", path], capture_output=True, text=True)
    elif IS_WSL_INSTALLED:
        result = subprocess.run(["wsl", "stat", "-c", "%s", path], capture_output=True, text=True)
    else:
        print_error("Error: The current OS is not Linux nor is WSL installed. Please run this script on a Linux system or install WSL.")
        return None
    if result.returncode != 0:
        raise FileNotFoundError(f"Path not found in WSL: {path}")
    return int(result.stdout.strip())


def remove_file(path):
    if not path_exists(path):
        return
    if IS_OS_LINUX:
        subprocess.run(["rm", "-f", path], check=True)
    elif IS_WSL_INSTALLED:
        subprocess.run(["wsl", "rm", "-f", path], check=True)
    else:
        print_error("This script requires Linux or WSL to remove POSIX paths.")


def read_linux_file_lines(path: str) -> list[str] | None:
    """
    Liest den Inhalt einer Datei zeilenweise über ein Linux-kompatibles Shell-Kommando.
    Gibt eine Liste der Zeilen zurück (wie readlines()), oder None bei Fehler.
    """
    try:
        if not (IS_OS_LINUX or IS_WSL_INSTALLED):
            raise EnvironmentError("Linux-kompatibles Lesen nur auf Linux/WSL erlaubt.")

        # Kommando vorbereiten
        command = f"cat {sh_escape(path)}"
        result = run_command(command, use_shell=True)

        if result is None or result.returncode != 0:
            print_error(f"[Fehler] Lesen der Datei fehlgeschlagen: {result.stderr if result else 'Unbekannter Fehler'}")
            return None
        split_lines = result.stdout.splitlines()
        for i in range(len(split_lines)):
            if not split_lines[i].endswith("\n"):
                split_lines[i] += "\n"

        return split_lines

    except Exception as e:
        print_error(f"[Fehler] Ausnahme beim Lesen der Datei: {e}")
        return None


def write_linux_file(path: str, content: str) -> bool:
    """
    Schreibt eine Datei über ein Linux-kompatibles Shell-Kommando.
    Nutzt 'run_command'. Der Pfad muss ein Linux-Pfad sein.
    """
    import os
    try:
        if not (IS_OS_LINUX or IS_WSL_INSTALLED):
            raise EnvironmentError("Linux-kompatibles Schreiben nur auf Linux/WSL erlaubt.")

        # Verzeichnis extrahieren und per mkdir -p erstellen
        dir_path = os.path.dirname(path)
        mkdir_command = f"mkdir -p {sh_escape(dir_path)}"
        result_mkdir = run_command(mkdir_command, use_shell=True)
        if result_mkdir.returncode != 0:
            print(f"[Fehler] mkdir fehlgeschlagen: {result_mkdir.stderr}")
            return False

        # Dateiinhalt mit printf sicher schreiben
        write_command = f"printf %s {sh_escape(content)} > {sh_escape(path)}"
        result_write = run_command(write_command, use_shell=True)
        if result_write.returncode != 0:
            print(f"[Fehler] Schreiben fehlgeschlagen: {result_write.stderr}")
            return False

        return True

    except Exception as e:
        print(f"[Fehler] Ausnahme beim Schreiben der Datei: {e}")
        return False


def sh_escape(s: str) -> str:

    """
    Escapes a string for safe use in a shell command in Linux or WSL.
    :param s:
    :return:
    """
    return "'" + s.replace("'", "'\\''") + "'"


def run_command(command, use_shell=False, debug=GLOBAL_DEBUG):
    try:
        if use_shell:
            if IS_OS_LINUX:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            elif IS_WSL_INSTALLED:
                result = subprocess.run(["wsl", "bash", "-c", command], capture_output=True, text=True, check=True)
            else:
                print_error("Error: The current OS is not Linux nor is WSL installed. Please run this script on a Linux system or install WSL.")
                return None
        else:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)

        if debug:
            print(result.stdout)
        return result

    except subprocess.CalledProcessError as e:
        print_error(f"Command {command} failed with error: {e.stderr}")
        return None

