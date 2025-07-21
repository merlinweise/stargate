from src.ssg_to_smg import check_target_reachability, save_smg_file
from stochasticparitygame import read_spg_from_file, StochasticParityGame
from simplestochasticgame import read_ssg_from_file
from spg_to_ssg_reduction import spg_to_ssg
from ssg_to_smg import ssg_to_smgspec
from benchmarking_global import benchmark_own_examples_for_correctness

# benchmark_own_examples_for_correctness(["raphael2.spg", "raphael3.spg"], [(0.0, 0.25), (0.0, 1/3)], use_global_path=True, debug=True)

spg = read_spg_from_file("small_deterministic.spg", use_global_path=True, debug=False)
ssg = spg_to_ssg(spg, print_alphas=True)