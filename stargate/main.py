from simplestochasticgame import read_ssg_from_file
from ssg_to_smg import ssg_to_smgspec, save_smg_file

ssg = read_ssg_from_file(file_name="temp.ssg", use_global_path=True, debug=False)