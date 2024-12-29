from pathlib import Path

from m4b_util.helpers import SegmentData
from m4b_util.helpers.finders import find_chapters, find_silence


fake_input = Path("Not-a-real-file")


def test_find_silence(silences_file_path):
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
        SegmentData(id=4, start_time=20.011, end_time=20.01, backing_file=silences_file_path,
                    file_start_time=20.011, file_end_time=20.01),
    ]
    actual = find_silence(silences_file_path, silence_duration=0.25)
    assert actual == expected


def test_silence_no_silence(variable_volume_segments_file_path):
    """Scan a file without silence."""
    expected = []
    actual = find_silence(variable_volume_segments_file_path)
    assert actual == expected


def test_silence_start_end_times(silences_file_path):
    """Scan specific parts of a file."""
    expected = [
        SegmentData(id=0, start_time=05.000, end_time=07.5, backing_file=silences_file_path,
                    file_start_time=05.00, file_end_time=07.5),
        SegmentData(id=1, start_time=10.000, end_time=12.6, backing_file=silences_file_path,
                    file_start_time=10.00, file_end_time=12.6),
    ]
    actual = find_silence(silences_file_path, start_time=4.0, end_time=12.6, silence_duration=0.25)
    assert actual == expected


def test_silence_nonsilence_ending(abrupt_ending_file_path):
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
    actual = find_silence(abrupt_ending_file_path, silence_duration=0.25)
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
