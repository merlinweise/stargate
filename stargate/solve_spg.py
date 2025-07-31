import argparse
from stochasticparitygame import read_spg_from_file
from spg_to_ssg_reduction import spg_to_ssg
from ssg_to_smg import ssg_to_smgspec, save_smg_file, check_target_reachability


def main():
    """
    Main function to transform a Stochastic Parity Game (SPG) to a Simple Stochastic Game (SSG), save it as an SMG file and solve it for target reachability.
    """
    parser = argparse.ArgumentParser(description="Transform SPG to SSG")
    parser.add_argument("input_file", help="Path to input .spg file")
    parser.add_argument("output_file", help="Path to output .smg file")
    parser.add_argument("--epsilon", type=float, default=1e-6, help="Epsilon parameter for the SPG to SSG reduction")
    parser.add_argument("--force", action="store_true", help="Force overwrite of output files if it exists")
    parser.add_argument("--version", type=int, default=1, help="SSG to SMG transformation version: Version (1) improved alternating, (2) older alternating, (3) synchronous")
    parser.add_argument("--spg_from_in_out_directory", action="store_true", help="Read SPG from in/out directory")
    parser.add_argument("--smg_to_in_out_directory", action="store_true", help="Write SSG to in/out directory")
    parser.add_argument("--print_alphas", action="store_true", help="Print alphas during SPG to SSG reduction")
    parser.add_argument("--print_vertex_mapping", action="store_true", help="Print mapping of SSG vertices to SMG states")


    args = parser.parse_args()

    spg = read_spg_from_file(args.input_file, use_global_path=args.spg_from_in_out_directory, debug=False)
    ssg = spg_to_ssg(spg=spg, epsilon=args.epsilon, print_alphas=args.print_alphas)
    smgspec = ssg_to_smgspec(ssg=ssg, version=args.version, debug=False, print_correspondingvertices=args.print_vertex_mapping)
    save_smg_file(smg_spec=smgspec, file_name=args.output_file, force=args.force, use_global_path=args.smg_to_in_out_directory, debug=False)
    check_target_reachability(smg_file=args.output_file, print_probabilities=True, use_global_path=args.smg_to_in_out_directory, debug=False)

if __name__ == "__main__":
    main()
