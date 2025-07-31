import argparse
from simplestochasticgame import read_ssg_from_file
from ssg_to_smg import ssg_to_smgspec, save_smg_file


def main():
    parser = argparse.ArgumentParser(description="Transform SPG to SSG")
    parser.add_argument("input_file", help="Path to input .ssg file")
    parser.add_argument("output_file", help="Path to output .smg file")
    parser.add_argument("--version", type=int, default=1, help="SSG to SMG transformation version: Version (1) improved alternating, (2) older alternating, (3) synchronous")
    parser.add_argument("--force", action="store_true", help="Force overwrite of output file if it exists")
    parser.add_argument("--ssg_from_in_out_directory", action="store_true", help="Read SSG from in/out directory")
    parser.add_argument("--smg_to_in_out_directory", action="store_true", help="Write SMG to in/out directory")
    parser.add_argument("--print_vertex_mapping", action="store_true", help="Print mapping of SSG vertices to SMG states")

    args = parser.parse_args()

    ssg = read_ssg_from_file(file_name=args.input_file, use_global_path=args.ssg_from_in_out_directory, debug=False)
    smgspec = ssg_to_smgspec(ssg=ssg, version=args.version, debug=False, print_correspondingvertices=args.print_vertex_mapping)
    save_smg_file(smg_spec=smgspec, file_name=args.output_file, force=args.force, use_global_path=args.smg_to_in_out_directory, debug=False)

if __name__ == "__main__":
    main()
