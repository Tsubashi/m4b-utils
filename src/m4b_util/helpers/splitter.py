"""The Splitter Class."""
from m4b_util.helpers import cover_utils
from m4b_util.helpers.parallel_ffmpeg import ParallelFFmpeg


def split(
        input_path,
        output_dir_path,
        segment_list,
        output_pattern="segment_{i:04d}.mp3",
        padding=0.0
):
    """
    Split a file into multiple, based on segments.

    Args:
        input_path (Path): Path to the input file.
        output_dir_path (Path): Path to the directory to place the output files.
        segment_list (list[Segment]): List of segments to split the file into.
        output_pattern (str): Output filename pattern (e.g. `segment_{i:04d}.mp3`)
        padding (float): Silence to add to the end of the segments once the original has been removed.
    """
    cover_utils.extract_cover(input_path, output_dir_path / "cover.png")

    # Generate task list
    tasks = list()
    for i, segment in enumerate(segment_list):
        time = segment.end_time - segment.start_time

        output_dir_path.mkdir(exist_ok=True)
        output_path = output_dir_path / output_pattern.format(i, i=i, title=segment.title)

        # Set up our FFMPEG command
        cmd = ["ffmpeg", "-ss", str(segment.start_time), "-t", str(time), "-i", input_path]

        # Check to see if we had a cover image. If so, include it
        if (output_dir_path / "cover.png").exists():
            cmd.extend(["-i", output_dir_path / "cover.png", "-map", "1:0"])

        # Add the guaranteed mappings
        cmd.extend(["-map", "0:a", "-map_chapters", "-1", "-y"])

        # If we have a title, add it to the metadata
        if segment.title:
            cmd.extend(["-metadata", f"title={segment.title}"])

        # Add padding at the end of the segment
        if padding > 0.0:
            cmd.extend(["-af", f"apad=pad_dur={padding}"])

        # Finish the command with our output path
        cmd.append(output_path)

        name = f"Splitting segment {i}"
        if segment.title:
            name += f" - {segment.title}"
        tasks.append({
            "name": name,
            "command": cmd
        })

    # Process splits in parallel
    p = ParallelFFmpeg(f"Splitting '{input_path.name}'")
    p.process(tasks)
