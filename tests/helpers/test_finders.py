from pathlib import Path

from m4b_util.helpers import SegmentData
from m4b_util.helpers.finders import find_chapters, find_silence
from m4b_util.helpers.finders.silence_finder import SilenceLineParser


fake_input = Path("Not-a-real-file")


def test_find_silence(silences_file_path):
    """Find silences in a file."""
    expected = [
        SegmentData(id=0, start_time=00.000, end_time=5.0, backing_file=silences_file_path,
                    file_start_time=00.00, file_end_time=5.0),
        SegmentData(id=1, start_time=05.000, end_time=10.0, backing_file=silences_file_path,
                    file_start_time=05.00, file_end_time=10.0),
        SegmentData(id=2, start_time=10.000, end_time=15.0, backing_file=silences_file_path,
                    file_start_time=10.00, file_end_time=15.0),
        SegmentData(id=3, start_time=15.000, end_time=20.011, backing_file=silences_file_path,
                    file_start_time=15.00, file_end_time=20.011),
    ]
    actual = find_silence(silences_file_path, silence_duration=0.25)
    assert actual == expected


def test_find_trimmed_silence(silences_file_path):
    """Find silences in a file."""
    expected = [
        SegmentData(id=0, start_time=00.000, end_time=02.5, backing_file=silences_file_path,
                    file_start_time=00.00, file_end_time=02.5),
        SegmentData(id=1, start_time=05.000, end_time=07.5, backing_file=silences_file_path,
                    file_start_time=05.00, file_end_time=07.5),
        SegmentData(id=2, start_time=10.000, end_time=12.5, backing_file=silences_file_path,
                    file_start_time=10.00, file_end_time=12.5),
        SegmentData(id=3, start_time=15.000, end_time=17.5, backing_file=silences_file_path,
                    file_start_time=15.00, file_end_time=17.5),
    ]
    actual = find_silence(silences_file_path, silence_duration=0.25, trim_silence=True)
    assert actual == expected


def test_silence_no_silence(variable_volume_segments_file_path):
    """Scan a file without silence."""
    expected = []
    actual = find_silence(variable_volume_segments_file_path)
    assert actual == expected


def test_silence_start_end_times(silences_file_path):
    """Scan specific parts of a file."""
    expected = [
        SegmentData(id=0, start_time=04.000, end_time=05.0, backing_file=silences_file_path,
                    file_start_time=04.00, file_end_time=05.0),
        SegmentData(id=1, start_time=05.000, end_time=10.0, backing_file=silences_file_path,
                    file_start_time=05.00, file_end_time=10.0),
        SegmentData(id=2, start_time=10.000, end_time=12.6, backing_file=silences_file_path,
                    file_start_time=10.00, file_end_time=12.6),
    ]
    actual = find_silence(silences_file_path, start_time=4.0, end_time=12.6, silence_duration=0.25)
    assert actual == expected


def test_trimmed_silence_start_end_times(silences_file_path):
    """Scan specific parts of a file."""
    expected = [
        SegmentData(id=0, start_time=05.000, end_time=07.5, backing_file=silences_file_path,
                    file_start_time=05.00, file_end_time=07.5),
        SegmentData(id=1, start_time=10.000, end_time=12.6, backing_file=silences_file_path,
                    file_start_time=10.00, file_end_time=12.6),
    ]
    actual = find_silence(silences_file_path, start_time=4.0, end_time=12.6, silence_duration=0.25, trim_silence=True)
    assert actual == expected


def test_trimmed_silence_nonsilence_ending(abrupt_ending_file_path):
    """Scan a file that ends in non-silence."""
    expected = [
        SegmentData(id=0, start_time=00.000, end_time=02.5, backing_file=abrupt_ending_file_path,
                    file_start_time=00.00, file_end_time=02.5),
        SegmentData(id=1, start_time=05.000, end_time=07.5, backing_file=abrupt_ending_file_path,
                    file_start_time=05.00, file_end_time=07.5),
        SegmentData(id=2, start_time=10.000, end_time=12.5, backing_file=abrupt_ending_file_path,
                    file_start_time=10.00, file_end_time=12.5),
        SegmentData(id=3, start_time=15.000, end_time=17.51, backing_file=abrupt_ending_file_path,
                    file_start_time=15.00, file_end_time=17.51),
    ]
    actual = find_silence(abrupt_ending_file_path, silence_duration=0.25, trim_silence=True)
    assert actual == expected


def test_silence_bad_file(tmp_path):
    """Scan a non-audio file."""
    fake_file = tmp_path / "fake.m4b"
    open(fake_file, 'a')
    expected = []
    actual = find_silence(fake_file)
    assert actual == expected


def test_find_chapters(chaptered_audio_file_path):
    """Read the chapter metadata into an object."""
    expected = [
        SegmentData(id=0, start_time=00.0, end_time=02.5, title="110Hz - Loud", backing_file=chaptered_audio_file_path,
                    file_start_time=00.0, file_end_time=02.5),
        SegmentData(id=1, start_time=02.5, end_time=05.0, title="110Hz - Soft", backing_file=chaptered_audio_file_path,
                    file_start_time=02.5, file_end_time=05.0),
        SegmentData(id=2, start_time=05.0, end_time=07.5, title="220Hz - Loud", backing_file=chaptered_audio_file_path,
                    file_start_time=05.0, file_end_time=07.5),
        SegmentData(id=3, start_time=07.5, end_time=10.0, title="220Hz - Soft", backing_file=chaptered_audio_file_path,
                    file_start_time=07.5, file_end_time=10.0),
        SegmentData(id=4, start_time=10.0, end_time=12.5, title="330Hz - Loud", backing_file=chaptered_audio_file_path,
                    file_start_time=10.0, file_end_time=12.5),
        SegmentData(id=5, start_time=12.5, end_time=15.0, title="330Hz - Soft", backing_file=chaptered_audio_file_path,
                    file_start_time=12.5, file_end_time=15.0),
        SegmentData(id=6, start_time=15.0, end_time=17.5, title="440Hz - Loud", backing_file=chaptered_audio_file_path,
                    file_start_time=15.0, file_end_time=17.5),
        SegmentData(id=7, start_time=17.5, end_time=19.999, title="440Hz - Soft",
                    file_start_time=17.5, file_end_time=19.999,
                    backing_file=chaptered_audio_file_path),
    ]
    assert find_chapters(chaptered_audio_file_path) == expected


def test_chapters_start_end_times(chaptered_audio_file_path):
    """Filter out chapters based on a custom start and end time."""
    expected = [
        SegmentData(id=2, start_time=05.0, end_time=07.5, title="220Hz - Loud", backing_file=chaptered_audio_file_path,
                    file_start_time=05.0, file_end_time=07.5),
        SegmentData(id=3, start_time=07.5, end_time=10.0, title="220Hz - Soft", backing_file=chaptered_audio_file_path,
                    file_start_time=07.5, file_end_time=10.0),
        SegmentData(id=4, start_time=10.0, end_time=12.5, title="330Hz - Loud", backing_file=chaptered_audio_file_path,
                    file_start_time=10.0, file_end_time=12.5),
    ]
    assert find_chapters(
        chaptered_audio_file_path,
        start_time=2.75,
        end_time=14.0
    ) == expected


def test_chapters_no_chapters(mp3_path):
    """Read an audio file that has no chapter data."""
    assert find_chapters(mp3_path / "1 - 110Hz.mp3") == []


def test_chapters_unreadable_file(fake_file):
    """Find no chapters in a non-audio file."""
    assert find_chapters(fake_file) == []


def test_invalid_silence_lines():
    """Make sure we won't use times that are outside the duration of the file."""
    lines = [
        "size=N/A time=00:00:02.00 bitrate=N/A",
        " silence_end: 9.5 ",
    ]
    parser = SilenceLineParser(0.0, 10.0)
    parser.parse_lines(lines)
    times = parser.get_segments()
    assert times == []


def test_trim_silence():
    """Make sure we can trim silence from the start and end of a file."""
    lines = [
        " silence_start: 1.5 ",
        " silence_end: 2.0 ",
        " silence_start: 3.5 ",
        " silence_end: 4.0 ",
        " silence_start: 5.5 ",
        " silence_end: 6.0 ",
        " silence_start: 7.5 ",
        " silence_end: 8.0 ",
        "size=N/A time=00:00:12.00 bitrate=N/A",
    ]
    parser = SilenceLineParser(0.0, 10.0, trim_silence=True)
    parser.parse_lines(lines)
    times = parser.get_segments()
    assert times == [(0.0, 1.5), (2.0, 3.5), (4.0, 5.5), (6.0, 7.5), (8.0, 10.0)]


def test_preserving_silence():
    """Make sure we can preserve silence at the end of a file."""
    lines = [
        " silence_start: 1.5 ",
        " silence_end: 2.0 ",
        " silence_start: 3.5 ",
        " silence_end: 4.0 ",
        " silence_start: 5.5 ",
        " silence_end: 6.0 ",
        " silence_start: 7.5 ",
        " silence_end: 8.0 ",
        "size=N/A time=00:00:12.00 bitrate=N/A",
    ]
    parser = SilenceLineParser(0.0, 10.0, trim_silence=False)
    parser.parse_lines(lines)
    times = parser.get_segments()
    assert times == [(0.0, 2.0), (2.0, 4.0), (4.0, 6.0), (6.0, 8.0), (8.0, 10.0)]


def test_avoiding_double_endings():
    """When we see a silence end while preserving silence, avoid adding an end marker if it is already there."""
    lines = [
        " silence_end: 2.0 ",
        " silence_end: 4.0 ",
        "size=N/A time=00:00:12.00 bitrate=N/A",
    ]
    parser = SilenceLineParser(0.0, 10.0, trim_silence=False)
    parser.parse_line(lines[0])
    parser.segment_ends.append(2.0)  # Introduce a fake end marker
    parser.parse_line(lines[1])
    times = parser.get_segments()
    assert times == [(0.0, 2.0), (2.0, 2.0), (4.0, 10.0)]
