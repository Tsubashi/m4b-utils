from unittest import mock

import pytest
import testhelpers

from m4b_util.helpers import ffprobe, SegmentData
from m4b_util.subcommands import labels


@pytest.fixture
def label_file_path(tmp_path):
    """A generic label file."""
    label_file = tmp_path / "labels.txt"
    with open(label_file, "w") as f:
        f.write("0.000000	0.000000	1 - 110Hz" "\n"
                "2.500000	2.500000	2 - 220Hz" "\n"
                "5.000000	5.000000	3 - 330Hz" "\n"
                "7.500000	7.500000	4 - 440Hz" "\n"
                "10.000000	10.000000	5 - 550Hz" "\n"
                "12.500000	12.500000	6 - 660Hz" "\n"
                "15.000000	15.000000	7 - 770Hz" "\n"
                "17.600000	19.999000	8 - 880Hz" "\n"
                )
    return label_file


def _run_labels_cmd(arg_list):
    """Patch the runtime arguments, then run the split command."""
    argv_patch = ["m4b-util", "labels"]
    argv_patch.extend(arg_list)

    with mock.patch("sys.argv", argv_patch):
        labels.run()


def test_segment_data_from_labels():
    """Convert labels to a list of segment data."""
    input_list = [
        "0.000000	0.000000	Start",
        "75.223314	75.223314	Segment 1",
        "186.845005	186.845005	Segment 2",
        "320.305723	320.305723	Segment 3",
        "408.632453	408.632453	Segment 4",
        "461.531429	461.531429	End"
    ]
    expected = [
        SegmentData(start_time=000.000, end_time=075.223, title="Start"),
        SegmentData(start_time=075.223, end_time=186.845, title="Segment 1"),
        SegmentData(start_time=186.845, end_time=320.306, title="Segment 2"),
        SegmentData(start_time=320.306, end_time=408.632, title="Segment 3"),
        SegmentData(start_time=408.632, end_time=461.531, title="Segment 4"),
        SegmentData(start_time=461.531, end_time=461.531, title="End"),
    ]
    actual = labels.segment_data_from_labels(input_list)
    assert actual == expected


def test_segment_data_from_labels_invalid_labels(capsys):
    """Convert labels to a list of segment data."""
    input_list = [
        "0.0000.00	0.000000	Start",
        "0.000000	0.000.000	StartAgain",
        "75.223314	75.223314	Segment 1",
        "186.845005	186.845005	Segment 2",
        "derp",
        "320.305723	320.305723	Segment 3",
        "408.632453	408.632453	",
        "461531429	461.531429	End"
    ]
    expected = [
        SegmentData(start_time=075.223, end_time=186.845, title="Segment 1"),
        SegmentData(start_time=186.845, end_time=320.306, title="Segment 2"),
        SegmentData(start_time=320.306, end_time=408.632, title="Segment 3"),
        SegmentData(start_time=408.632, end_time=461531429., title=""),
        SegmentData(start_time=461531429., end_time=461.531, title="End"),
    ]
    actual = labels.segment_data_from_labels(input_list)
    assert actual == expected

    output = capsys.readouterr()
    for expected in ["Could not parse label:", "Start", "StartAgain", "derp"]:
        assert expected in output.out


def test_labels_from_segment_data():
    """Create a list of labels from a list of segment data."""
    input_list = [
        SegmentData(start_time=000.000, end_time=075.223, title="Start"),
        SegmentData(start_time=075.223, end_time=186.845, title="Segment 1"),
        SegmentData(start_time=186.845, end_time=320.306, title="Segment 2"),
        SegmentData(start_time=320.306, end_time=408.632),
        SegmentData(start_time=408.632, end_time=461.531, title=""),
        SegmentData(start_time=461.531, end_time=461.531, title="End"),
    ]
    expected = [
        "0.0	0.0	Start",
        "75.223	75.223	Segment 1",
        "186.845	186.845	Segment 2",
        "320.306	320.306	None",
        "408.632	408.632	",
        "461.531	461.531	End"
    ]
    actual = labels.labels_from_segment_data(input_list)
    assert actual == expected


def test_labels_from_labels(tmp_path, label_file_path, variable_volume_segments_file_path):
    """Generate all possible outputs from the label command, using a label file as input."""
    meta_file_path = tmp_path / "ffmetadata"
    label_out_path = tmp_path / "labels.out.txt"
    _run_labels_cmd([
        "--from-label-file", str(label_file_path),
        "--to-metadata-file", str(meta_file_path),
        "--to-label-file", str(label_out_path),
        "--to-book", str(variable_volume_segments_file_path)
    ])

    # Check metadata file
    expected_metadata = (
        ";FFMETADATA1\n"
        "major_brand=M4A\n"
        "minor_version=512\n"
        "compatible_brands=M4A isomiso2\n"
        "title=None\n"
        "artist=None\n"
        "album=None\n"
        "date=None\n"
        "genre=Audiobook\n"
        "[CHAPTER]\n"        "TIMEBASE=1/1000\n"        "START=0\n"           "END=2500\n"        "title=1 - 110Hz\n"
        "[CHAPTER]\n"        "TIMEBASE=1/1000\n"        "START=2500\n"        "END=5000\n"        "title=2 - 220Hz\n"
        "[CHAPTER]\n"        "TIMEBASE=1/1000\n"        "START=5000\n"        "END=7500\n"        "title=3 - 330Hz\n"
        "[CHAPTER]\n"        "TIMEBASE=1/1000\n"        "START=7500\n"        "END=10000\n"       "title=4 - 440Hz\n"
        "[CHAPTER]\n"        "TIMEBASE=1/1000\n"        "START=10000\n"       "END=12500\n"       "title=5 - 550Hz\n"
        "[CHAPTER]\n"        "TIMEBASE=1/1000\n"        "START=12500\n"       "END=15000\n"       "title=6 - 660Hz\n"
        "[CHAPTER]\n"        "TIMEBASE=1/1000\n"        "START=15000\n"       "END=17600\n"       "title=7 - 770Hz\n"
        "[CHAPTER]\n"        "TIMEBASE=1/1000\n"        "START=17600\n"       "END=19999\n"       "title=8 - 880Hz\n"
    )
    with open(meta_file_path) as f:
        metadata = f.read()
    assert metadata == expected_metadata

    # Check Label file
    expected_labeldata = (
        "0.0	0.0	1 - 110Hz" "\n"
        "2.5	2.5	2 - 220Hz" "\n"
        "5.0	5.0	3 - 330Hz" "\n"
        "7.5	7.5	4 - 440Hz" "\n"
        "10.0	10.0	5 - 550Hz" "\n"
        "12.5	12.5	6 - 660Hz" "\n"
        "15.0	15.0	7 - 770Hz" "\n"
        "17.6	17.6	8 - 880Hz" "\n"
    )
    with open(label_out_path) as f:
        labeldata = f.read()
    assert labeldata == expected_labeldata

    # Check audiobook output
    probe = ffprobe.run_probe(variable_volume_segments_file_path)
    assert probe and len(probe.chapters) == 8
    assert probe.chapters[0]["tags"]["title"] == "1 - 110Hz"
    assert probe.chapters[1]["tags"]["title"] == "2 - 220Hz"
    assert probe.chapters[2]["tags"]["title"] == "3 - 330Hz"
    assert probe.chapters[3]["tags"]["title"] == "4 - 440Hz"
    assert probe.chapters[4]["tags"]["title"] == "5 - 550Hz"
    assert probe.chapters[5]["tags"]["title"] == "6 - 660Hz"
    assert probe.chapters[6]["tags"]["title"] == "7 - 770Hz"
    assert probe.chapters[7]["tags"]["title"] == "8 - 880Hz"


def test_labels_from_book(tmp_path, chaptered_audio_file_path, expected_data, variable_volume_segments_file_path):
    """Generate all possible outputs from the label command, using an audiobook file as input."""
    meta_file_path = tmp_path / "ffmetadata"
    label_out_path = tmp_path / "labels.out.txt"
    _run_labels_cmd([
        "--from-book", str(chaptered_audio_file_path),
        "--to-metadata-file", str(meta_file_path),
        "--to-label-file", str(label_out_path),
        "--to-book", str(variable_volume_segments_file_path)
    ])

    # Check metadata file
    with open(meta_file_path) as f:
        metadata = f.read()
    assert metadata == expected_data["chaptered"]["metadata"]

    # Check Label file
    expected_labeldata = (
        "0.0	0.0	110Hz - Loud" "\n"
        "2.5	2.5	110Hz - Soft" "\n"
        "5.0	5.0	220Hz - Loud" "\n"
        "7.5	7.5	220Hz - Soft" "\n"
        "10.0	10.0	330Hz - Loud" "\n"
        "12.5	12.5	330Hz - Soft" "\n"
        "15.0	15.0	440Hz - Loud" "\n"
        "17.5	17.5	440Hz - Soft" "\n"
    )
    with open(label_out_path) as f:
        labeldata = f.read()
    assert labeldata == expected_labeldata

    # Check audiobook output
    probe = ffprobe.run_probe(variable_volume_segments_file_path)
    assert probe and len(probe.chapters) == 8
    assert probe.chapters[0]['tags']['title'] == "110Hz - Loud"
    assert probe.chapters[1]['tags']['title'] == "110Hz - Soft"
    assert probe.chapters[2]['tags']['title'] == "220Hz - Loud"
    assert probe.chapters[3]['tags']['title'] == "220Hz - Soft"
    assert probe.chapters[4]['tags']['title'] == "330Hz - Loud"
    assert probe.chapters[5]['tags']['title'] == "330Hz - Soft"
    assert probe.chapters[6]['tags']['title'] == "440Hz - Loud"
    assert probe.chapters[7]['tags']['title'] == "440Hz - Soft"


def test_labels_overshoot(label_file_path, abrupt_ending_file_path):
    """Trim labels that extend beyond file when writing to book. Truncate those that begin inside, but end outside."""""
    _run_labels_cmd([
        "--from-label-file", str(label_file_path),
        "--to-book", str(abrupt_ending_file_path)
    ])
    # Check audiobook output
    probe = ffprobe.run_probe(abrupt_ending_file_path)
    assert probe and len(probe.chapters) == 7
    assert probe.chapters[0]['tags']['title'] == "1 - 110Hz"
    assert probe.chapters[1]['tags']['title'] == "2 - 220Hz"
    assert probe.chapters[2]['tags']['title'] == "3 - 330Hz"
    assert probe.chapters[3]['tags']['title'] == "4 - 440Hz"
    assert probe.chapters[4]['tags']['title'] == "5 - 550Hz"
    assert probe.chapters[5]['tags']['title'] == "6 - 660Hz"
    assert probe.chapters[6]['tags']['title'] == "7 - 770Hz"
    assert probe.chapters[6]['end_time'] == "17.500000"


def test_labels_no_output(label_file_path, tmp_path):
    """Don't write any files if no output is specified."""
    _run_labels_cmd(["--from-label-file", str(label_file_path)])
    expected_files = [label_file_path.name]
    testhelpers.check_output_folder(tmp_path, expected_files, check_func=testhelpers.assert_file_path_is_file)
