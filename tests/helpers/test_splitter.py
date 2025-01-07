import shutil

import testhelpers

from m4b_util.helpers import ffprobe, SegmentData, splitter


def test_splitter(silences_file_path, tmp_path):
    """Split a file into four parts."""
    output_path = tmp_path / "output"
    segment_list = [
        SegmentData(id=0, start_time=0.0, end_time=2.5),
        SegmentData(id=1, start_time=2.5, end_time=5.0),
        SegmentData(id=2, start_time=5.0, end_time=7.5),
        SegmentData(id=3, start_time=7.5, end_time=10.),

    ]
    expected_files = [
        "segment_0000.mp3",
        "segment_0001.mp3",
        "segment_0002.mp3",
        "segment_0003.mp3",
    ]
    splitter.split(
        input_path=silences_file_path,
        output_dir_path=output_path,
        segment_list=segment_list,
    )
    testhelpers.check_output_folder(output_path=output_path, expected_files=expected_files)


def test_splitter_with_cover(silences_file_path, test_data_path, tmp_path):
    """Split a file into one part, making sure to include the cover image."""
    output_path = tmp_path / "output"
    out_file_path = output_path / "segment_0000.mp3"
    # Copy in the cover file
    output_path.mkdir(exist_ok=True)
    shutil.copy(test_data_path / "cover.png", output_path / "cover.png")
    segment_list = [
        SegmentData(id=0, start_time=0.0, end_time=2.5),
    ]
    splitter.split(
        input_path=silences_file_path,
        output_dir_path=output_path,
        segment_list=segment_list,
    )
    probe = ffprobe.run_probe(out_file_path)
    assert probe
    assert probe.streams[1]['codec_name'] == "png"


def test_alternate_output_pattern(silences_file_path, tmp_path):
    """Split a file into four parts, with custom naming rules."""
    output_path = tmp_path / "output"
    segment_list = [
        SegmentData(id=0, start_time=0.0, end_time=2.5),
        SegmentData(id=1, start_time=2.5, end_time=5.0, title="Frist"),
        SegmentData(id=2, start_time=5.0, end_time=7.5),
        SegmentData(id=3, start_time=7.5, end_time=10., title="Secnod"),

    ]
    expected_files = [
        "00 - None.mp3",
        "01 - Frist.mp3",
        "02 - None.mp3",
        "03 - Secnod.mp3",
    ]
    splitter.split(
        input_path=silences_file_path,
        output_dir_path=output_path,
        segment_list=segment_list,
        output_pattern="{i:02d} - {title}.mp3"
    )
    testhelpers.check_output_folder(output_path=output_path, expected_files=expected_files)


def test_overlapping_output_names(silences_file_path, tmp_path):
    """Overwrite files if the naming pattern causes collisions."""
    def check_func(input_file_path):
        """Check for correct file length."""
        probe = ffprobe.run_probe(input_file_path)
        # Truncate the duration to an int to allow the test to pass even if the duration is slightly off.
        # This happened on GHA where Ubuntu shows 5.04 and Windows shows 5.04225.
        assert int(float(probe.audio['duration'])) == 5
    output_path = tmp_path / "output"
    segment_list = [
        SegmentData(id=0, start_time=0.0, end_time=2.5),
        SegmentData(id=1, start_time=2.5, end_time=5.0, title="Frist"),
        SegmentData(id=2, start_time=5.0, end_time=5.5),
        SegmentData(id=3, start_time=5.5, end_time=10.5, title="Secnod"),

    ]
    expected_files = [
        "Collided_File.mp3",
    ]
    splitter.split(
        input_path=silences_file_path,
        output_dir_path=output_path,
        segment_list=segment_list,
        output_pattern="Collided_File.mp3",
    )

    testhelpers.check_output_folder(output_path=output_path, expected_files=expected_files, check_func=check_func)


def test_title_metadata(silences_file_path, tmp_path):
    """Split a file into four parts with custom title names."""
    def check_func(input_file_path):
        probe = ffprobe.run_probe(input_file_path)
        assert input_file_path.stem == probe.tags["title"]
    output_path = tmp_path / "output"
    segment_list = [
        SegmentData(id=0, start_time=0.0, end_time=2.5, title="segment_0000"),
        SegmentData(id=1, start_time=2.5, end_time=5.0, title="segment_0001"),
        SegmentData(id=2, start_time=5.0, end_time=7.5, title="segment_0002"),
        SegmentData(id=3, start_time=7.5, end_time=10., title="segment_0003"),

    ]
    expected_files = [
        "segment_0000.mp3",
        "segment_0001.mp3",
        "segment_0002.mp3",
        "segment_0003.mp3",
    ]
    splitter.split(
        input_path=silences_file_path,
        output_dir_path=output_path,
        segment_list=segment_list,
    )
    testhelpers.check_output_folder(output_path=output_path, expected_files=expected_files, check_func=check_func)


def test_padding(silences_file_path, tmp_path):
    """Split a file into four parts with padding."""
    def check_func(input_file_path):
        probe = ffprobe.run_probe(input_file_path)
        assert probe.data["format"]["duration"] == "3.024000"
    output_path = tmp_path / "output"
    segment_list = [
        SegmentData(id=0, start_time=0.0, end_time=2.5, title="segment_0000"),
        SegmentData(id=1, start_time=2.5, end_time=5.0, title="segment_0001"),
        SegmentData(id=2, start_time=5.0, end_time=7.5, title="segment_0002"),
        SegmentData(id=3, start_time=7.5, end_time=10., title="segment_0003"),

    ]
    expected_files = [
        "segment_0000.mp3",
        "segment_0001.mp3",
        "segment_0002.mp3",
        "segment_0003.mp3",
    ]
    splitter.split(
        input_path=silences_file_path,
        output_dir_path=output_path,
        segment_list=segment_list,
        padding=0.5,
    )
    testhelpers.check_output_folder(output_path=output_path, expected_files=expected_files, check_func=check_func)
