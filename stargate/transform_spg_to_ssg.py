import argparse
from simplestochasticgame import save_ssg_file, ssg_to_ssgspec
from stochasticparitygame import read_spg_from_file
from spg_to_ssg_reduction import spg_to_ssg


def main():
    parser = argparse.ArgumentParser(description="Transform SPG to SSG")
    parser.add_argument("input_file", help="Path to input .spg file")
    parser.add_argument("output_file", help="Path to output .ssg file")
    parser.add_argument("--epsilon", type=float, default=1e-6, help="Epsilon parameter for the reduction")
    parser.add_argument("--force", action="store_true", help="Force overwrite of output file if it exists")
    parser.add_argument("--spg_from_in_out_directory", action="store_true", help="Read SPG from in/out directory")
    parser.add_argument("--ssg_to_in_out_directory", action="store_true", help="Write SSG to in/out directory")
    parser.add_argument("--print_alphas", action="store_true", help="Print alphas during conversion")

    args = parser.parse_args()

    spg = read_spg_from_file(args.input_file, use_global_path=args.spg_from_in_out_directory, debug=False)
    ssg = spg_to_ssg(spg=spg, epsilon=args.epsilon, print_alphas=args.print_alphas)
    ssgspec = ssg_to_ssgspec(ssg=ssg)
    save_ssg_file(ssg_spec=ssgspec, file_name=args.output_file, use_global_path=args.ssg_to_in_out_directory, force=args.force, debug=False)

if __name__ == "__main__":
    main()
