"""Chapter Finder."""
from m4b_util.helpers import ffprobe
from m4b_util.helpers.segment_data import SegmentData


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
