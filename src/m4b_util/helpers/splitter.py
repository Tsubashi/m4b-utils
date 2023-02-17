"""The Splitter Class."""
from m4b_util.helpers import cover_utils
from m4b_util.helpers.parallel_ffmpeg import ParallelFFmpeg


def split(
        input_path,
        output_dir_path,
        segment_list,
        padding=0.,
        output_pattern="segment_{i:04d}.mp3"
):
    """Split a file into multiple, based on segments."""
    cover_utils.extract_cover(input_path, output_dir_path / "cover.png")

    # Generate task list
    tasks = list()
    for i, segment in enumerate(segment_list):
        time = segment.end_time - segment.start_time

        output_dir_path.mkdir(exist_ok=True)
        output_path = output_dir_path / output_pattern.format(i, i=i, title=segment.title)

        cmd = ["ffmpeg", "-ss", str(segment.start_time), "-t", str(time), "-i", input_path,
               "-map", "0:a", "-map_chapters", "-1", "-y"]
        if segment.title:
            cmd.extend(["-metadata", f"title={segment.title}"])

        if padding > 0.:
            cmd.extend(["-af", f"apad=pad_dur={padding}"])
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
