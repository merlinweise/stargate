import os
import subprocess

GLOBAL_IN_OUT_PATH = "/mnt/c/Uni_Zeug/6.Semester/Bachelorarbeit/PRISMgames_testing/program_in_and_out"  # needs to be in Linux format
GLOBAL_IN_OUT_PATH_WIN = "C:\\Uni_Zeug\\6.Semester\\Bachelorarbeit\\PRISMgames_testing\\program_in_and_out"  # needs to be in Windows format
GLOBAL_DEBUG = False
PRINT_VERTEX_CREATION_WARNINGS = False
ENSURE_EVE_AND_ADAM_VERTICES = True
PRISM_EPSILON = 1e-6
PRISM_PATH = "/mnt/c/Uni_Zeug/6.Semester/Bachelorarbeit/prism_extension/Algorithms-For-Stochastic-Games/prism-games-3.0.beta-src/prism/bin/prism"
PRISM_SOLVING_ALGORITHM = "GAUSS_SEIDEL_VALUE_ITERATION"  # "VALUE_ITERATION" or "GAUSS_SEIDEL_VALUE_ITERATION" or "POLICY_ITERATION" or "MODIFIED_POLICY_ITERATION" or "INTERVAL_ITERATION" or "SOUND_VALUE_ITERATION" or "TOPOLOGICAL VALUE_ITERATION" or "SOUND_TOPOLOGICAL_VALUE_ITERATION" or "SOUND_POLICY_ITERATION" or "SOUND_MODIFIED_POLICY_ITERATION"


# ----------------------------------------------------------------------------------------------------------------


IS_OS_LINUX = os.name == 'posix'
if not IS_OS_LINUX:
    # Test if WSL is installed
    result = subprocess.run(["wsl", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    IS_WSL_INSTALLED = result.returncode == 0
if not IS_OS_LINUX and not IS_WSL_INSTALLED:
    print("Error: The current OS is not Linux nor is WSL installed. Please run this script on a Linux system or install WSL.")
match PRISM_SOLVING_ALGORITHM:
    case "VALUE_ITERATION":
        PRISM_SOLVING_ALGORITHM = "-valiter"
    case "GAUSS_SEIDEL_VALUE_ITERATION":
        PRISM_SOLVING_ALGORITHM = "-gaussseidel"
    case "POLICY_ITERATION":
        PRISM_SOLVING_ALGORITHM = "-politer"
    case "MODIFIED_POLICY_ITERATION":
        PRISM_SOLVING_ALGORITHM = "-modpoliter"
    case "INTERVAL_ITERATION":
        PRISM_SOLVING_ALGORITHM = "-intervaliter"
    case "SOUND_VALUE_ITERATION":
        PRISM_SOLVING_ALGORITHM = "-soundvaliter"
    case "TOPOLOGICAL VALUE_ITERATION":
        PRISM_SOLVING_ALGORITHM = "-topovaliter"
    case _:
        PRISM_SOLVING_ALGORITHM = ""
