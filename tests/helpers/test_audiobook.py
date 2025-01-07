"""Test the Audiobook class."""
from pathlib import Path
import shutil
from subprocess import run
from tempfile import TemporaryDirectory

from natsort import natsorted
import testhelpers

from m4b_util.helpers import Audiobook, ffprobe, SegmentData


def _do_dir_scan(book, in_dir, use_filenames=False, decode_durations=False, **kwargs):
    """Read book from directory, then test the book's attributes based on kwargs."""
    book.add_chapters_from_directory(in_dir, use_filenames, decode_durations)
    _check_attrs(book, **kwargs)


def _do_file_scan(book, file_list, use_filenames=False, decode_durations=False, **kwargs):
    """Read book from a list of files, then test the book's attributes based on kwargs."""
    book.add_chapters_from_filelist(file_list, use_filenames, decode_durations)
    _check_attrs(book, **kwargs)


def _check_attrs(book, **kwargs):
    """Check book's attrs against the provided kwargs."""
    testhelpers.soften_backing_file(book.chapters)
    for attr_name, attr_value in kwargs.items():
        assert (getattr(book, attr_name) == attr_value)


def _add_metadata(file_path, **kwargs):
    """Add metadata specified by kwargs to file_path."""
    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / f"temp{file_path.suffix}"
        cmd = ["ffmpeg", "-i", file_path]

        # Add in metadata from kwargs
        for key, value in kwargs.items():
            cmd.append("-metadata")
            cmd.append(f"{key}={value}")

        # Add output path
        cmd.append(tmp_path)

        run(cmd, capture_output=True, check=True)

        shutil.move(tmp_path, file_path)


def test_suggested_file_name():
    """Set the output path in various ways."""
    b = Audiobook()
    assert (str(b.suggested_file_name) == "None - None.m4b")  # Default
    # Author
    b.author = "Write-y McAuthor"
    assert (str(b.suggested_file_name) == "Write-y McAuthor - None.m4b")
    # Author + Title
    b.title = "Test Book: An exercise of m4b-util"
    assert (str(b.suggested_file_name) == "Write-y McAuthor - Test Book: An exercise of m4b-util.m4b")
    # Name (Overwrites Author & Title), Adds m4b extension
    b.output_name = "Author McWrite-y"
    assert (str(b.suggested_file_name) == "Author McWrite-y.m4b")
    # Name (Overwrites Author & Title), does not double up m4b extension
    b.output_name = "Author McWrite-y.m4b"
    assert (str(b.suggested_file_name) == "Author McWrite-y.m4b")


def test_file_scanner_mp3(mp3_path, expected_data):
    """Get the correct data from a set of mp3 files."""
    b = Audiobook()
    _do_dir_scan(
        b,
        mp3_path,
        title=None,
        author=None,
        date=None,
        chapters=expected_data['mp3']['chapters'],
    )
    # Verify that scanning twice doubles the chapters
    _do_dir_scan(
        b,
        mp3_path,
        title=None,
        author=None,
        date=None,
        chapters=expected_data['mp3']['chapters_doubled'],
    )


def test_file_scanner_wav(wav_path, expected_data):
    """Get the correct data from a set of mp3 files."""
    b = Audiobook()
    _do_dir_scan(
        b,
        wav_path,
        title=None,
        author=None,
        date=None,
        chapters=expected_data['default']['chapters'],
        metadata=expected_data['default']['metadata']
    )
    # Verify that scanning twice doubles the chapters
    _do_dir_scan(
        b,
        wav_path,
        title=None,
        author=None,
        date=None,
        chapters=expected_data['default']['chapters_doubled'],
    )


def test_file_scanner_m4a(m4a_path, expected_data):
    """Get the correct data from a set of mp3 files."""
    b = Audiobook()
    _do_dir_scan(
        b,
        m4a_path,
        title=None,
        author=None,
        date=None,
        chapters=expected_data['default']['chapters'],
        metadata=expected_data['default']['metadata']
    )
    # Verify that scanning twice doubles the chapters
    _do_dir_scan(
        b,
        m4a_path,
        title=None,
        author=None,
        date=None,
        chapters=expected_data['default']['chapters_doubled'],
    )


def test_single_file_scanner(chaptered_audio_file_path, expected_data):
    """Get the correct data from a single, chaptered file."""
    b = Audiobook()
    b.add_chapters_from_chaptered_file(chaptered_audio_file_path)
    _check_attrs(
        b,
        title="Chaptered Audio",
        author="m4b-util",
        date="2022",
        chapters=expected_data['chaptered']['chapters'],
        metadata=expected_data['chaptered']['metadata']
    )
    b.add_chapters_from_chaptered_file(chaptered_audio_file_path)
    _check_attrs(b, chapters=expected_data['chaptered']['chapters_doubled'])


def test_file_scanner_use_filenames(mp3_path, expected_data):
    """Use filenames instead of metadata when scanning files."""
    b = Audiobook()
    _do_dir_scan(
        b,
        mp3_path,
        use_filenames=True,
        title=None,
        author=None,
        date=None,
        chapters=expected_data['use_filename']['chapters'],
    )


def test_metadata_from_input(mp3_file_path):
    """Pick up metadata from our input files."""
    _add_metadata(mp3_file_path, album="Book Title", artist="Author McWrite-y", date="2022")
    _do_file_scan(
        Audiobook(),
        [mp3_file_path],
        title="Book Title",
        author="Author McWrite-y",
        date="2022"
    )


def test_grab_first_metadata_only(mp3_path):
    """Only fill metadata items the first time we see them."""
    file = mp3_path / "2 - 220Hz.mp3"
    _add_metadata(file, album="Book Title", artist="Author McWrite-y")
    second_file = mp3_path / "3 - 330Hz.mp3"
    _add_metadata(second_file, album="Fake Book Title", artist="Not a Real Author")
    _do_dir_scan(
        Audiobook(),
        mp3_path,
        title="Book Title",
        author="Author McWrite-y"
    )


def test_prefer_user_supplied_metadata(mp3_file_path):
    """Don't fill metadata from files if we already have it."""
    _add_metadata(mp3_file_path, album="Fake Book Title", artist="Not Author McWrite-y", date="1011")
    b = Audiobook()
    b.title = "Book Title"
    b.author = "Author McWrite-y"
    b.date = "2022"
    _do_file_scan(
        b,
        [mp3_file_path],
        title="Book Title",
        author="Author McWrite-y",
        date="2022"
    )


def test_scanning_nonaudio_file(mp3_path, capsys):
    """Print a warning if we can't parse a file."""
    # Create a blank mp3 file
    open(mp3_path / "not-really-audio.mp3", 'a').close()
    _do_dir_scan(Audiobook(), mp3_path)
    output = capsys.readouterr()
    assert ("Warning: Unable to parse" in output.out)


def test_status_updates_during_scan(wav_path, capsys):
    """Show the user what we are doing while we scan."""
    _do_dir_scan(Audiobook(), wav_path)
    output = capsys.readouterr()
    assert (output.out == "Collecting file data...\nFile scan complete.\n")


def test_concatenation(m4a_path):
    """Concatenate all the files into one."""
    b = Audiobook()
    temp_files = natsorted(m4a_path.glob("*"))
    out_file_path = b._concatenate_files(temp_files)

    probe = ffprobe.run_probe(out_file_path)
    assert probe
    assert probe.format['duration'] == "40.021333"
    assert probe.audio['duration'] == "40.021333"
    assert not probe.tags.get('title')


def test_filenames_with_single_quotes(m4a_path):
    """Create a well-formed file when one of the inputs has quotes in its name."""
    orig_file = m4a_path / "2 - 220Hz.m4a"
    quote_file = m4a_path / "2 - '220Hz'.m4a"
    shutil.move(orig_file, quote_file)

    b = Audiobook()
    temp_files = natsorted(m4a_path.glob("*"))
    out_file_path = b._concatenate_files(temp_files)

    probe = ffprobe.run_probe(out_file_path)
    assert probe
    assert probe.format['duration'] == "40.021333"
    assert probe.audio['duration'] == "40.021333"  # If the file is broken, this will be shorter
    assert not probe.tags.get('title')


def test_add_chapter_info(m4a_path):
    """Add chapter info to a file."""
    file = m4a_path / "4 - 440Hz.m4a"
    b = Audiobook()
    b.chapters.append(SegmentData(title="Sound", start_time=0, end_time=2.499))
    b.chapters.append(SegmentData(title="Silence", start_time=2.5, end_time=4.999))
    out_file_path = b._add_chapter_info(file)

    probe = ffprobe.run_probe(out_file_path)
    assert probe
    assert len(probe.chapters) == 2
    assert probe.chapters[0]['tags']['title'] == "Sound"
    assert probe.chapters[1]['tags']['title'] == "Silence"


def test_ffmpeg_fail():
    """Handle it when an ffmpeg run fails."""
    b = Audiobook()
    tmp_path = b._tmp_path
    with testhelpers.expect_exit():
        b._run_ffmpeg(["ffmpeg", "-invalid_option"], "Make ffmpeg fail.")

    # Make sure tmp path is gone
    assert not tmp_path.exists()


def test_ffmpeg_fail_keep_temp_files():
    """Handle it when an ffmpeg run fails."""
    b = Audiobook()
    b.keep_temp_files = True
    canary = Path(b._tmp_path) / "canary"
    open(canary, 'a').close()
    with testhelpers.expect_exit():
        b._run_ffmpeg(["ffmpeg", "-invalid_option"], "Make ffmpeg fail.")
    expected_files = ["canary"]
    testhelpers.check_output_folder(b._tmp_path, expected_files, check_func=testhelpers.assert_file_path_is_file)


def test_bind_no_files(capsys):
    """Show an error when there are no files to bind."""
    b = Audiobook()
    assert (b.bind("/not-a-real-file") is False)
    output = capsys.readouterr()
    assert ("Nothing to bind" in output.out)


def test_bind_keep_temp_files(mp3_path, tmp_path, test_data_path, capsys):
    """Keep all temp files when asked."""
    out_file_path = tmp_path / "Book.m4b"
    b = Audiobook(
        cover=test_data_path / "cover.png",
        keep_temp_files=True
    )
    b.add_chapters_from_directory(mp3_path)
    b.bind(out_file_path)

    # Make sure we told the user where the temp dir is
    output = capsys.readouterr()
    assert ("Temp files can be found at" in output.out)

    # Make sure the files we expect are there
    expected_files = (
        "0_1 - 110Hz.m4a",
        "1_2 - 220Hz.m4a",
        "2_3 - 330Hz.m4a",
        "3_4 - 440Hz.m4a",
        "4_5 - 550Hz.m4a",
        "5_6 - 660Hz.m4a",
        "6_7 - 770Hz.m4a",
        "7_8 - 880Hz.m4a",
        "long.m4a",
        "filelist",
        "coverless.m4b",
        "finished.m4b",
        "ffmetadata",
    )
    testhelpers.check_output_folder(b._tmp_path, expected_files, check_func=testhelpers.assert_file_path_is_file)


def test_bind_coverless(mp3_path, tmp_path):
    """Create an audiobook without a cover."""
    out_file_path = tmp_path / "Book.m4b"
    b = Audiobook()
    b.add_chapters_from_directory(mp3_path)
    b.bind(out_file_path)

    # Verify output
    probe = ffprobe.run_probe(out_file_path)
    assert probe

    # Check chapters
    assert len(probe.chapters) == 8
    assert probe.chapters[0]['tags']['title'] == "1"
    assert probe.chapters[1]['tags']['title'] == "2"
    assert probe.chapters[2]['tags']['title'] == "3"
    assert probe.chapters[3]['tags']['title'] == "4"
    assert probe.chapters[4]['tags']['title'] == "5"
    assert probe.chapters[5]['tags']['title'] == "6"
    assert probe.chapters[6]['tags']['title'] == "7"
    assert probe.chapters[7]['tags']['title'] == "8"

    # Check duration
    assert probe.format['duration'] == "40.021333"
    assert probe.audio['duration'] == "40.021333"

    # Check metadata
    assert probe.tags['title'] == "None"
    assert probe.tags['artist'] == "None"
    assert probe.tags['album'] == "None"
    assert probe.tags['date'] == "None"
    assert probe.tags['genre'] == "Audiobook"


def test_bind_covered(mp3_path, tmp_path, test_data_path):
    """Create an audiobook with a cover."""
    out_file_path = tmp_path / "Book.m4b"
    b = Audiobook(cover=test_data_path / "cover.png")
    b.add_chapters_from_directory(mp3_path)
    b.bind(out_file_path)

    # Verify output
    probe = ffprobe.run_probe(out_file_path)
    assert probe

    # Check chapters
    assert len(probe.chapters) == 8
    assert probe.chapters[0]['tags']['title'] == "1"
    assert probe.chapters[1]['tags']['title'] == "2"
    assert probe.chapters[2]['tags']['title'] == "3"
    assert probe.chapters[3]['tags']['title'] == "4"
    assert probe.chapters[4]['tags']['title'] == "5"
    assert probe.chapters[5]['tags']['title'] == "6"
    assert probe.chapters[6]['tags']['title'] == "7"
    assert probe.chapters[7]['tags']['title'] == "8"

    # Check duration
    assert probe.format['duration'] == "40.021333"
    assert probe.audio['duration'] == "40.021333"

    # Check metadata
    assert probe.tags['title'] == "None"
    assert probe.tags['artist'] == "None"
    assert probe.tags['album'] == "None"
    assert probe.tags['date'] == "None"

    # Check cover
    assert probe.streams[2]['codec_name'] == "png"


def test_rebind_single_file(chaptered_audio_file_path, tmp_path):
    """Rebind an audiobook with changed chapter metadata."""
    b = Audiobook()
    b.add_chapters_from_chaptered_file(chaptered_audio_file_path)
    b.chapters[2].title = "NEW"
    out_path = tmp_path / "rebind.m4b"
    b.bind(out_path)

    # Verify output
    probe = ffprobe.run_probe(out_path)
    assert probe

    # Check chapters
    assert len(probe.chapters) == 8
    assert probe.chapters[0]['tags']['title'] == "110Hz - Loud"
    assert probe.chapters[1]['tags']['title'] == "110Hz - Soft"
    assert probe.chapters[2]['tags']['title'] == "NEW"
    assert probe.chapters[3]['tags']['title'] == "220Hz - Soft"
    assert probe.chapters[4]['tags']['title'] == "330Hz - Loud"
    assert probe.chapters[5]['tags']['title'] == "330Hz - Soft"
    assert probe.chapters[6]['tags']['title'] == "440Hz - Loud"
    assert probe.chapters[7]['tags']['title'] == "440Hz - Soft"

    # Check duration
    assert probe.format['duration'] == "20.000000"
    assert probe.audio['duration'] == "20.000000"

    # Check metadata
    assert probe.tags['title'] == "Chaptered Audio"
    assert probe.tags['artist'] == "m4b-util"
    assert probe.tags['album'] == "Chaptered Audio"
    assert probe.tags['date'] == "2022"


def test_rebind_single_file_selections(chaptered_audio_file_path, tmp_path):
    """Create an audiobook out of selections from a single file."""
    b = Audiobook()
    b.add_chapters_from_chaptered_file(chaptered_audio_file_path)
    del b.chapters[2]
    out_path = tmp_path / "selections.m4b"
    b.bind(out_path)
    # Verify output
    probe = ffprobe.run_probe(out_path)
    assert probe

    # Check chapters
    assert len(probe.chapters) == 7
    assert probe.chapters[0]['tags']['title'] == "110Hz - Loud"
    assert probe.chapters[1]['tags']['title'] == "110Hz - Soft"
    assert probe.chapters[2]['tags']['title'] == "220Hz - Soft"
    assert probe.chapters[3]['tags']['title'] == "330Hz - Loud"
    assert probe.chapters[4]['tags']['title'] == "330Hz - Soft"
    assert probe.chapters[5]['tags']['title'] == "440Hz - Loud"
    assert probe.chapters[6]['tags']['title'] == "440Hz - Soft"

    # Check duration
    assert probe.format['duration'] == "17.520333"
    assert probe.audio['duration'] == "17.520333"

    # Check metadata
    assert probe.tags['title'] == "Chaptered Audio"
    assert probe.tags['artist'] == "m4b-util"
    assert probe.tags['album'] == "Chaptered Audio"
    assert probe.tags['date'] == "2022"


def test_bad_cover(tmp_path, m4a_path):
    """Throw an error if we can't add the specified cover."""
    out_file_path = tmp_path / "Book.m4b"
    cover_path = tmp_path / "not-really-a-cover.png"
    open(cover_path, 'a').close()
    b = Audiobook(cover=cover_path)
    b.add_chapters_from_directory(m4a_path)
    with testhelpers.expect_exit():
        b.bind(out_file_path)


def test_bind_titleless_segments(tmp_path, mp3_path):
    """Allow binding, even if a segment data has no title.

    In real life, this is unlikely to happen, since all the scanner methods set the title, but it is possible to set
    the segment list manually, so we need to handle it.
    """
    out_file_path = tmp_path / "Book.m4b"
    b = Audiobook()
    b.add_chapters_from_directory(mp3_path)
    # Remove Chapter titles before we bind.
    for chapter in b.chapters:
        chapter.title = None
    b.bind(out_file_path)

    # Verify output
    probe = ffprobe.run_probe(out_file_path)
    assert probe

    # Check chapters
    assert len(probe.chapters) == 8
    assert probe.chapters[0]['tags']['title'] == "1"
    assert probe.chapters[1]['tags']['title'] == "2"
    assert probe.chapters[2]['tags']['title'] == "3"
    assert probe.chapters[3]['tags']['title'] == "4"
    assert probe.chapters[4]['tags']['title'] == "5"
    assert probe.chapters[5]['tags']['title'] == "6"
    assert probe.chapters[6]['tags']['title'] == "7"
    assert probe.chapters[7]['tags']['title'] == "8"

    # Check duration
    assert probe.format['duration'] == "40.021333"
    assert probe.audio['duration'] == "40.021333"

    # Check metadata
    assert probe.tags['title'] == "None"
    assert probe.tags['artist'] == "None"
    assert probe.tags['album'] == "None"
    assert probe.tags['date'] == "None"
    assert probe.tags['genre'] == "Audiobook"


def test_bind_non_backed_segment(tmp_path, mp3_path, capsys):
    """Alert the user if attempting to bind with a non-backed segment."""
    out_file_path = tmp_path / "Book.m4b"
    b = Audiobook()
    b.add_chapters_from_directory(mp3_path)
    # Remove backing files before we bind.
    for chapter in b.chapters:
        chapter.backing_file = None
    assert b.bind(out_file_path) is False
    output = capsys.readouterr()
    assert "Cannot bind a non-backed segment." in output.out


def test_filelist_duration_failure(mkv_file_path, capsys):
    """Warn user if we fail to find duration of a file while adding chapters."""
    b = Audiobook()
    b.add_chapters_from_filelist([mkv_file_path])
    output = capsys.readouterr()
    assert "Failed to determine duration" in output.out


def test_add_fake_chaptered_file(fake_file, capsys):
    """Warn user if we cannot read the chaptered file while adding."""
    b = Audiobook()
    b.add_chapters_from_chaptered_file(fake_file)
    output = capsys.readouterr()
    assert "Unable to parse" in output.out
    assert len(b.chapters) == 0


def test_get_cover_in_chapter_dir(test_data_path, m4a_path):
    """Search out image files named "cover" when importing chapters from a directory."""
    cover_file_path = m4a_path / "cover.png"
    shutil.copy(test_data_path / "cover.png", cover_file_path)
    _do_dir_scan(
        Audiobook(),
        m4a_path,
        cover=cover_file_path
    )


def test_noncover_image_in_chapter_dir(test_data_path, m4a_path):
    """Ignore images not named "cover" when importing chapters from a directory."""
    cover_file_path = m4a_path / "not-a-cover.png"
    shutil.copy(test_data_path / "cover.png", cover_file_path)
    _do_dir_scan(
        Audiobook(),
        m4a_path,
        cover=None
    )


def test_wrong_file_ext_cover_image_in_chapter_dir(test_data_path, m4a_path):
    """Ignore cover images with the wrong extensions when importing chapters from a directory."""
    cover_file_path = m4a_path / "cover.tiff"
    shutil.copy(test_data_path / "cover.png", cover_file_path)
    _do_dir_scan(
        Audiobook(),
        m4a_path,
        cover=None
    )


def test_tmp_path():
    """Create a temporary directory when we need it, even if it was removed."""
    b = Audiobook()
    # Create the temp dir by accessing the property
    tmp_path = b._tmp_path
    assert tmp_path.is_dir()

    # Delete the temp dir
    shutil.rmtree(tmp_path)
    assert not tmp_path.exists()

    # Recreate the deleted temp dir by accessing the property again
    new_tmp_path = b._tmp_path
    assert new_tmp_path == tmp_path
    assert tmp_path.is_dir()
