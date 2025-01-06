import argparse
from pathlib import Path
import sys

from rich import print

from ..helpers import splitter
from ..helpers.finders import find_chapters, find_silence


def _parse_args():
    parser = argparse.ArgumentParser(
        prog="m4b-util split",
        description='Split media into segments.'
    )
    parser.add_argument('mode', help='modes: s - silence, c - chapters')
    parser.add_argument('input_file', help='Input filename')

    parser.add_argument('-e', "--end-time", type=float, help='End time (seconds)')
    parser.add_argument('-m', "--minimum-segment-time", type=float, default=1.0,
                        help='Smallest segment size to consider, in seconds.')
    parser.add_argument('-o', "--output-dir", type=str, help="Directory to place output.")
    parser.add_argument('-p', '--output-pattern', type=str, default="segment_{i:04d}.mp3",
                        help="Output filename pattern (e.g. `segment_{i:04d}.mp3`), use '{i}' for sequence and "
                             "'{title}' for chapter title.")
    parser.add_argument('-s', "--start-time", type=float, help='Start time (seconds)')

    silence_options = parser.add_argument_group('split-by-silence options')
    silence_options.add_argument("--silence-threshold", default=-35, type=int, help='Silence threshold (in dB)')
    silence_options.add_argument("--silence-duration", default=3.0, type=float, help='Silence duration')
    silence_options.add_argument("--padding", default=0.0, type=float,
                                 help='Silence to add to the end of the segments once the original has been removed.')
    silence_options.add_argument("--trim-silence", action="store_true", default=False,
                                 help='Remove silence from the start and end of segments.')

    return parser.parse_args(sys.argv[2:])


def run():
    """Split an audio file into pieces, based on silence."""
    args = _parse_args()
    input_path = Path(args.input_file)
    segment_list = None

    # Step 1: Look for where the splits should be.
    if args.mode.lower() in ["s", "silence", "silences"]:
        segment_list = find_silence(
            input_path=input_path,
            start_time=args.start_time,
            end_time=args.end_time,
            silence_duration=args.silence_duration,
            silence_threshold=args.silence_threshold,
            trim_silence=args.trim_silence,
        )
    elif args.mode.lower() in ["c", "chapter", "chapters"]:
        segment_list = find_chapters(
            input_path=input_path,
            start_time=args.start_time,
            end_time=args.end_time,
        )
    else:
        print(f"[bold red]Error:[/] Unexpected mode '{args.mode}'")
        exit(1)

    if not segment_list:
        print("[bold red]Error:[/] No segments found.")
        exit(1)

    # Step 2: Filter out too-small segments
    # Use .copy() so that we can modify the original without throwing off the iterator
    for segment in segment_list.copy():
        if segment.end_time - segment.start_time < args.minimum_segment_time:
            segment_list.remove(segment)
    if len(segment_list) == 0:
        print("[bold red]Error:[/] Not enough segments found.")
        exit(1)

    # Step 3: Split the original file
    print(f"[yellow]Info:[/] Found [yellow]{len(segment_list)}[/] segments")
    if args.output_dir:
        output_path = Path(args.output_dir)
    else:
        output_path = Path()
    splitter.split(
        input_path=input_path,
        output_dir_path=output_path,
        output_pattern=args.output_pattern,
        segment_list=segment_list,
        padding=args.padding
    )
