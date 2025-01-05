"""Chapter Finder."""
import re

from m4b_util.helpers import ffprobe, ffprogress
from m4b_util.helpers.segment_data import SegmentData


def _parse_silence_lines(lines, start_time, end_time):
    """Parse the output of the silencedetect filter."""
    silence_start_re = re.compile(r' silence_start: (?P<start>[0-9]+(\.?[0-9]*))$')
    silence_end_re = re.compile(r' silence_end: (?P<end>[0-9]+(\.?[0-9]*)) ')
    total_duration_re = re.compile(
        r'size=[^ ]+ time=(?P<hours>[0-9]{2}):(?P<minutes>[0-9]{2}):(?P<seconds>[0-9\.]{5}) bitrate=')
    # Segments start when silence ends, and segments end when silence starts.
    segment_starts = []
    segment_ends = []
    duration = 10000000000000.0
    end_time = end_time or duration  # Ensure end_time has a value.
    for line in lines:
        # Check for silence start
        silence_start_match = silence_start_re.search(line)
        if silence_start_match:
            timestamp = start_time + float(silence_start_match.group('start'))
            if timestamp > start_time:
                segment_ends.append(timestamp)
                if len(segment_starts) == 0:
                    # Started with non-silence.
                    segment_starts.append(start_time)
            continue

        # Check for silence end
        silence_end_match = silence_end_re.search(line)
        if silence_end_match:
            timestamp = start_time + float(silence_end_match.group('end'))
            if timestamp < end_time and timestamp < duration:
                segment_starts.append(timestamp)
        total_duration_match = total_duration_re.search(line)

        # Check for duration
        if total_duration_match:
            hours = int(total_duration_match.group('hours'))
            minutes = int(total_duration_match.group('minutes'))
            seconds = float(total_duration_match.group('seconds'))
            duration = hours * 3600 + minutes * 60 + seconds + start_time

    if len(segment_starts) > len(segment_ends):
        # If we've got a valid segment start with no segment end, we can assume the input ended without silence.
        # That means we need to add the duration as the final segment end time.
        if segment_starts[-1] < duration:
            segment_ends.append(duration)
        else:
            # If we do have a segment start that is beyond the duration, then we should just remove it.
            segment_starts.pop()

    segment_list = list(zip(segment_starts, segment_ends))
    return segment_list


def find_silence(input_path, start_time=None, end_time=None, silence_duration=3.0, silence_threshold=-35):
    """Finds silence in a file and generates a list of SegmentData's representing the non-silence portions."""
    # Run ffmpeg's silencedetect filter
    cmd = ["ffmpeg"]
    if start_time:
        cmd.extend(["-ss", str(start_time)])
    else:
        # If start_time isn't set, then we don't need it in the command, but we do need a default later.
        start_time = 0.0
    cmd.extend(["-i", input_path])
    if end_time:
        end_time_dur = end_time - start_time
        cmd.extend(["-t", str(end_time_dur)])
    cmd.extend([
        "-filter_complex",
        f"[0]silencedetect=d={silence_duration}:n={silence_threshold}dB[s0]",
        "-map", "[s0]",
        "-f", "null",
        "-"
    ])
    ff = ffprogress.run(cmd, "Detecting Silence")

    # Check to see if ffmpeg exited abnormally
    lines = []
    if ff:
        lines = ff.output.splitlines()

    times = _parse_silence_lines(lines, start_time, end_time)

    # Generate SegmentData list
    retval = list()
    for i, (segment_start, segment_end) in enumerate(times):
        retval.append(SegmentData(
            start_time=segment_start,
            end_time=segment_end,
            id=i,
            backing_file=input_path,
            file_start_time=segment_start,
            file_end_time=segment_end
        ))
    return retval


def find_chapters(input_path, start_time=None, end_time=None):
    """Read chapter metadata from a file and generates a list of matching SegmentData's."""
    # Process defaults here, since we often get passed argparse values directly.
    if start_time is None:
        start_time = 0.0
    if end_time is None:
        end_time = 100000000000000.0
    probe = ffprobe.run_probe(input_path)
    if probe is None:
        return []  # If we can't read the file, then we didn't find any chapters.
    chapter_list = list()
    for chapter in probe.chapters:
        title = chapter.get("tags", dict()).get("title")
        if float(chapter['start_time']) >= start_time and float(chapter['end_time']) <= end_time:
            chapter_list.append(SegmentData(
                start_time=float(chapter['start_time']),
                end_time=float(chapter['end_time']),
                id=chapter['id'],
                title=title,
                backing_file=input_path,
                file_start_time=float(chapter['start_time']),
                file_end_time=float(chapter['end_time'])
            ))
    return chapter_list
