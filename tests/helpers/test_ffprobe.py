"""ffprobe tests."""
import pytest

from m4b_util.helpers import ffprobe


def test_video_only(video_only_file):
    """Read in a video-only file."""
    probe = ffprobe.run_probe(video_only_file)
    assert probe.audio is None
    expected_tags = {
        'compatible_brands': 'isomiso2avc1mp41',
        'major_brand': 'isom',
        'minor_version': '512'
    }
    del probe.tags['encoder']  # Encoder will be different depending on the version of ffmpeg
    assert probe.tags == expected_tags


def test_probe_data(mp3_path):
    """Read an mp3 file."""
    file = mp3_path / "6 - 660Hz.mp3"
    probe = ffprobe.run_probe(file)
    assert probe

    expected = {
        'chapters': [],
        'format': {
            'bit_rate': '64374',
            'duration': '5.040000',
            'format_long_name': 'MP2/3 (MPEG audio layer 2/3)',
            'format_name': 'mp3',
            'nb_programs': 0,
            'nb_stream_groups': 0,
            'nb_streams': 1,
            'probe_score': 51,
            'size': '40556',
            'start_time': '0.023021',
            'tags': {}
        },
        'streams': [{
            'avg_frame_rate': '0/0',
            'bit_rate': '64000',
            'bits_per_sample': 0,
            'channel_layout': 'mono',
            'channels': 1,
            'codec_long_name': 'MP3 (MPEG audio layer 3)',
            'codec_name': 'mp3',
            'codec_tag': '0x0000',
            'codec_tag_string': '[0][0][0][0]',
            'codec_type': 'audio',
            'disposition': {
                'attached_pic': 0,
                'captions': 0,
                'clean_effects': 0,
                'comment': 0,
                'default': 0,
                'dependent': 0,
                'descriptions': 0,
                'dub': 0,
                'forced': 0,
                'hearing_impaired': 0,
                'karaoke': 0,
                'lyrics': 0,
                'metadata': 0,
                'non_diegetic': 0,
                'original': 0,
                'still_image': 0,
                'timed_thumbnails': 0,
                'visual_impaired': 0
            },
            'duration': '5.040000',
            'duration_ts': 71124480,
            'index': 0,
            'initial_padding': 0,
            'r_frame_rate': '0/0',
            'sample_fmt': 'fltp',
            'sample_rate': '48000',
            'start_pts': 324870,
            'start_time': '0.023021',
            'time_base': '1/14112000'
        }]
    }
    # Remove items that can change between tests
    del probe.data['format']['filename']
    del probe.data['format']['tags']['encoder']

    # Remove items that are different between GHA runners
    if 'multilayer' in probe.data['streams'][0]['disposition']:
        del probe.data['streams'][0]['disposition']['multilayer']

    assert (probe.data == expected)


def test_probe_blank_file(fake_file):
    """Return None when run on an un-parsable file."""
    probe = ffprobe.run_probe(fake_file)
    assert not probe


def test_decode_durations(m4a_file_path):
    """Read the duration of a file by decoding it."""
    meta_duration = ffprobe.get_file_duration(m4a_file_path)
    decoded_duration = ffprobe.get_file_duration(m4a_file_path, decode_duration=True)
    assert (meta_duration == pytest.approx(decoded_duration, 0.05) == 5.0)


def test_decode_duration_fake_file(fake_file):
    """Read the duration of a file by decoding it."""
    with pytest.raises(RuntimeError) as e:
        ffprobe.get_file_duration(fake_file, decode_duration=True)
    assert ("Could not get audio stream." in str(e.value))


def test_get_duration_no_metadata(mkv_file_path, capsys):
    """Throw an error if no duration metadata, such as in mkv's."""
    # Make sure it reads successfully if decode_durations is set
    assert (ffprobe.get_file_duration(mkv_file_path, decode_duration=True) == 5.0)

    # Make sure it doesn't work when decode_durations is not set
    with pytest.raises(RuntimeError) as e:
        ffprobe.get_file_duration(mkv_file_path)
    assert ("Cannot parse duration listed in file." in str(e.value))
