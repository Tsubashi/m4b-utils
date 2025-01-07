"""Test the split subcommand."""
from contextlib import contextmanager
import os
from pathlib import Path
from unittest import mock

import testhelpers

from m4b_util.subcommands import split


@contextmanager
def change_cwd(new_path):
    """Change to a new directory, then change back when finished."""
    owd = Path.cwd()  # Original Working Directory
    os.chdir(new_path)
    try:
        yield
    finally:
        os.chdir(owd)


def _run_split_cmd(arg_list):
    """Patch the runtime arguments, then run the split command."""
    argv_patch = ["m4b-util", "split"]
    argv_patch.extend(arg_list)

    with mock.patch("sys.argv", argv_patch):
        split.run()


@mock.patch("m4b_util.subcommands.split.find_silence")
def test_silence_modes(finder_mock):
    """Run in silence-split mode."""
    finder_mock.return_value = None
    for mode in ["s", "silence", "silences"]:
        with testhelpers.expect_exit():
            _run_split_cmd([mode, "Not-really-a-file"])
        finder_mock.assert_called_once()
        finder_mock.reset_mock()


@mock.patch("m4b_util.subcommands.split.find_chapters")
def test_chapter_modes(finder_mock):
    """Run in chapter-split mode."""
    finder_mock.return_value = None
    for mode in ["c", "chapter", "chapters"]:
        with testhelpers.expect_exit():
            _run_split_cmd([mode, "Not-really-a-file"])
        finder_mock.assert_called_once()
        finder_mock.reset_mock()


def test_unexpected_mode(capsys):
    """Alert the user if an unexpected mode is requested."""
    with testhelpers.expect_exit_with_output(capsys, "Unexpected mode"):
        _run_split_cmd(["not-a-real-mode", "Not-really-a-file"])


def test_split_silence(tmp_path, silences_file_path):
    """Split a file on silence, default settings."""
    output_path = tmp_path / "output"
    output_path.mkdir()
    expected_files = [
        "segment_0000.mp3",
        "segment_0001.mp3",
        "segment_0002.mp3",
        "segment_0003.mp3",
    ]
    with change_cwd(output_path):
        _run_split_cmd(["silence", str(silences_file_path), "--silence-duration", "1.0"])
        testhelpers.check_output_folder(output_path, expected_files)


def test_split_chapter(tmp_path, chaptered_audio_file_path):
    """Split a file on silence, default settings."""
    output_path = tmp_path / "output"
    output_path.mkdir()
    expected_files = [
        "segment_0000.mp3",
        "segment_0001.mp3",
        "segment_0002.mp3",
        "segment_0003.mp3",
        "segment_0004.mp3",
        "segment_0005.mp3",
        "segment_0006.mp3",
        "segment_0007.mp3",
    ]
    with change_cwd(output_path):
        _run_split_cmd(["chapter", str(chaptered_audio_file_path)])
        testhelpers.check_output_folder(output_path, expected_files)


def test_split_audio_start_end_times(tmp_path, chaptered_audio_file_path):
    """Split a file, with start and end times specified."""
    output_path = tmp_path / "output"
    _run_split_cmd([
        "chapter",
        str(chaptered_audio_file_path),
        "-o", str(output_path),
        "-s", "1.75",
        "-e", "5.03"
    ])
    testhelpers.check_output_folder(output_path)


def test_split_audio_fail(fake_file, tmp_path, capsys):
    """Exit with non-zero code when asked to process a non-audio file."""
    with testhelpers.expect_exit_with_output(capsys, "No segments found"):
        _run_split_cmd(["silence", str(fake_file), "-o", str(tmp_path)])


def test_split_audio_duration(tmp_path, silences_file_path):
    """Adjust silence duration limits."""
    output_path = tmp_path / "output"
    cmd = [
        "silence",
        str(silences_file_path),
        "-o", str(output_path),
        "--silence-duration", "1.5"
    ]
    expected_files = (
        "segment_0000.mp3",
        "segment_0001.mp3",
        "segment_0002.mp3",
        "segment_0003.mp3",
    )
    _run_split_cmd(cmd)
    testhelpers.check_output_folder(output_path, expected_files)


def test_split_audio_threshold_lower(tmp_path, variable_volume_segments_file_path, capsys):
    """Adjust silence threshold limits to a threshold lower than any noise in the file."""
    output_path = tmp_path / "output"
    cmd = [
        "silence",
        str(variable_volume_segments_file_path),
        "-o", str(output_path),
        "--silence-threshold", "-45",
        "--silence-duration", "1.5"
    ]
    with testhelpers.expect_exit_with_output(capsys, "No segments found."):
        _run_split_cmd(cmd)


def test_split_audio_threshold_higher(tmp_path, variable_volume_segments_file_path, capsys):
    """Adjust silence threshold limits to a threshold higher than any noise in the file."""
    output_path = tmp_path / "output"
    cmd = [
        "silence",
        str(variable_volume_segments_file_path),
        "-o", str(output_path),
        "--silence-threshold", "-5",
        "--silence-duration", "1.5",
        "--trim-silence"
    ]
    with testhelpers.expect_exit_with_output(capsys, "No segments found."):
        _run_split_cmd(cmd)


def test_split_audio_threshold(tmp_path, variable_volume_segments_file_path):
    """Adjust silence threshold limits to a threshold right between the two volume levels in the file."""
    output_path = tmp_path / "output"
    cmd = [
        "silence",
        str(variable_volume_segments_file_path),
        "-o", str(output_path),
        "--silence-threshold", "-20",
        "--silence-duration", "1.5"
    ]
    expected_files = (
        "segment_0000.mp3",
        "segment_0001.mp3",
        "segment_0002.mp3",
        "segment_0003.mp3",
    )
    _run_split_cmd(cmd)
    testhelpers.check_output_folder(output_path, expected_files)


def test_split_audio_segment_pattern(tmp_path, silences_file_path):
    """Specify a non-default segment pattern."""
    output_path = tmp_path / "output"
    cmd = [
        "silence",
        str(silences_file_path),
        "-o", str(output_path),
        "--silence-duration", "1.5",
        "-p", "chunk_{:02d}.mp3",
    ]
    # Make sure the files we expect are there
    expected_files = (
        "chunk_00.mp3",
        "chunk_01.mp3",
        "chunk_02.mp3",
        "chunk_03.mp3",
    )
    _run_split_cmd(cmd)
    testhelpers.check_output_folder(output_path, expected_files)


def test_minimum_segment_size(tmp_path, silences_file_path, capsys):
    """Reject segments lower than the specified minimum size."""
    output_path = tmp_path / "output"
    cmd = [
        "silence",
        str(silences_file_path),
        "-o", str(output_path),
        "--silence-duration", "1.5",
        "--minimum-segment-time", "12",
        "-p", "chunk_{:02d}.mp3",
    ]
    with testhelpers.expect_exit_with_output(capsys, "Not enough segments found."):
        _run_split_cmd(cmd)
