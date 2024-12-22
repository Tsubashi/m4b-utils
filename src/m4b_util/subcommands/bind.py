"""Bind Command."""
import argparse
from pathlib import Path
import sys

from rich import print

from m4b_util.helpers import Audiobook


def _parse_args():
    """Parse all arguments."""
    parser = argparse.ArgumentParser(
        description="Take a folder of audio files and output an m4b.",
        prog="m4b-util bind"
    )
    parser.add_argument('input_folder', type=str, help="The folder of input files.")
    parser.add_argument('-a', "--author", type=str, help="Name of the author.")
    parser.add_argument('-c', "--cover", type=str, help="Image file to use as cover")
    parser.add_argument('-o', "--output-dir", type=str, help="Directory to put the finished audiobook.")
    parser.add_argument('-n', "--output-name", type=str, help="Filename to use for finished audiobook. Default"
                                                              " is '[Author] - [Title].m4b'.")
    parser.add_argument('-t', "--title", type=str, help="Title of the audiobook.")
    parser.add_argument("--date", type=str, help="Date to include in metadata.")
    parser.add_argument("--decode-durations", "--decode-duration", action='store_true', default=False,
                        help="Fully decode each file to determine its duration (Slower, but more accurate).")
    parser.add_argument("--show-order", action='store_true',
                        help="Show the order the files would be read in, then exit.")
    parser.add_argument("--keep-temp-files", action='store_true', help="Skip cleanup. (Debugging)")
    parser.add_argument("--use-filename", "--use-filenames", action='store_true', default=False,
                        help="Use the filename as the chapter title instead of the title from the file's metadata.")

    return parser.parse_args(sys.argv[2:])


def run():
    """Entrypoint for bind subcommand."""
    args = _parse_args()

    # Make sure the output directory exists, if it was specified.
    if args.output_dir and not Path(args.output_dir).is_dir():
        print(f"[bold red]Error:[/] '{args.output_dir}' is not a directory.")
        return -1

    # Set info from args
    book = Audiobook(
        author=args.author,
        cover=args.cover,
        output_name=args.output_name,
        title=args.title,
        date=args.date,
        keep_temp_files=args.keep_temp_files,
    )

    # Print order, if applicable
    if args.show_order:
        for i, file in enumerate(book.scan_dir(args.input_folder)):
            print(f"{i:3}:\t{file.name}")
        return 0

    # Add the files to the binder
    book.add_chapters_from_directory(
        input_dir=args.input_folder,
        use_filenames=args.use_filename,
        decode_durations=args.decode_durations
    )

    # Run the binder
    output_path = Path()
    if args.output_dir:
        output_path = Path(args.output_dir)
    output_path = output_path / book.suggested_file_name
    if book.bind(output_path=output_path):
        # Tell the user where it is.
        print(f"[cyan]Writing '[yellow]{output_path}[/]'")

    return 0
