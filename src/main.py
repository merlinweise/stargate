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