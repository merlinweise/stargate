# import simpleparitygame
import simplestochasticgame
# import spg_to_ssg_reduction
import ssg_to_smg
import re
import subprocess
import platform
import os
import time
from error_handling import print_warning, print_error










convert_ssg_to_png("raphael.ssg", force=True, ssg_to_smg_version1=False, debug=True, create_png=True, open_png=True)
#spg=simple_parity_game.read_spg_from_file("C:\\Uni_Zeug\\6.Semester\\Bachelorarbeit\\PRISMgames_testing\\program_input\\elbeck.spg")

#print(spg_to_ssg_reduction.compute_alphas_for_spg(spg=spg))