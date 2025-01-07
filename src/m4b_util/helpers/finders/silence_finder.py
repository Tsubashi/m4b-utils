"""Chapter Finder."""
import re

from m4b_util.helpers import ffprogress
from m4b_util.helpers.segment_data import SegmentData

FAKE_DURATION = 10000000000000.0  # Default to a very large number until we know the real duration.
silence_start_re = re.compile(r' silence_start: (?P<start>[0-9]+(\.?[0-9]*))')
silence_end_re = re.compile(r' silence_end: (?P<end>[0-9]+(\.?[0-9]*))')
total_duration_re = re.compile(
    r'size=[^ ]+ time=(?P<hours>[0-9]{2}):(?P<minutes>[0-9]{2}):(?P<seconds>[0-9\.]{5}) bitrate=')


class SilenceLineParser:
    """Utility class for parsing ffmpeg's silencedetect filter output."""
    def __init__(self, start_time, end_time, trim_silence=False):
        self.start_time = start_time or 0.0
        self.end_time = end_time or FAKE_DURATION
        self.trim_silence = trim_silence
        self.segment_starts = []
        self.segment_ends = []
        self.duration = FAKE_DURATION

    def parse_line(self, line):
        """Parse a single line of silencedetect output."""
        self._check_for_start(line)
        self._check_for_end(line)
        self._check_for_duration(line)

    def _check_for_start(self, line):
        """Check for silence start. Only applies if we're trimming silence."""
        if self.trim_silence:
            silence_start_match = silence_start_re.search(line)
            if silence_start_match:
                timestamp = self.start_time + float(silence_start_match.group('start'))
                if self.start_time < timestamp < self.end_time:
                    self.segment_ends.append(timestamp)
                    if len(self.segment_starts) == 0:
                        # Started with non-silence.
                        self.segment_starts.append(self.start_time)

    def _check_for_duration(self, line):
        total_duration_match = total_duration_re.search(line)
        if total_duration_match:
            hours = int(total_duration_match.group('hours'))
            minutes = int(total_duration_match.group('minutes'))
            seconds = float(total_duration_match.group('seconds'))
            self.duration = hours * 3600 + minutes * 60 + seconds + self.start_time
            if self.end_time == FAKE_DURATION:
                self.end_time = self.duration

    def _check_for_end(self, line):
        silence_end_match = silence_end_re.search(line)
        if silence_end_match:
            timestamp = self.start_time + float(silence_end_match.group('end'))
            # end_time could theoretically be set further than the actual duration, so we need to check both.
            if timestamp < self.end_time and timestamp < self.duration:
                if not self.trim_silence:
                    # If we're not trimming silence, segments won't get marked as ended elsewhere.
                    if len(self.segment_starts) == 0:
                        self.segment_starts.append(self.start_time)
                    # If we have an existing segment, it will need to be marked as ending here.
                    if len(self.segment_starts) > len(self.segment_ends):
                        self.segment_ends.append(timestamp)

                # Mark the new segment too
                self.segment_starts.append(timestamp)

    def parse_lines(self, lines):
        """Parse a list of lines."""
        for line in lines:
            self.parse_line(line)

    def get_segments(self):
        """Return the list of segments."""
        if len(self.segment_starts) > len(self.segment_ends):
            # If we've got a valid segment start with no segment end, we can assume the input ended without silence.
            # That means we need to add the global end time as the final segment end time.
            if self.segment_starts[-1] < self.duration:
                self.segment_ends.append(self.end_time)
            else:
                # If we do have a segment start that is beyond the duration, then we should just remove it.
                self.segment_starts.pop()

        segment_list = list(zip(self.segment_starts, self.segment_ends))
        return segment_list


def find_silence(
        input_path,
        start_time=None,
        end_time=None,
        silence_duration=3.0,
        silence_threshold=-35,
        trim_silence=False):
    """
    Finds silence in a file and generates a list of SegmentData's representing the non-silence portions.

    Args:
        input_path (Path): Path to the input file.
        start_time (float): Time to start processing from.
        end_time (float): Time to stop processing at.
        silence_duration (float): Duration of silence to detect.
        silence_threshold (float): Silence threshold in dB.
        trim_silence (bool): If True, silence will be trimmed from the start and end of the segments.
    """
    # Run ffmpeg's silencedetect filter
    cmd = ["ffmpeg"]
    if start_time:
        cmd.extend(["-ss", str(start_time)])
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

    # Parse the output
    line_parser = SilenceLineParser(start_time, end_time, trim_silence)
    line_parser.parse_lines(lines)
    times = line_parser.get_segments()

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
