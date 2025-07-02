from src.ssg_to_smg import check_target_reachability, save_smg_file
from stochasticparitygame import read_spg_from_file
from spg_to_ssg_reduction import spg_to_ssg
from ssg_to_smg import ssg_to_smgspec
spg = read_spg_from_file("test_for_only_eve_vertices.spg", use_global_path=True)
ssg = spg_to_ssg(spg=spg, print_alphas=True, epsilon=1e-6)
smgspec = ssg_to_smgspec(ssg=ssg)
save_smg_file(smgspec, "test_for_only_eve_vertices.smg", use_global_path=True, force=True)
check_target_reachability("test_for_only_eve_vertices.smg", True, False, use_global_path=True)
