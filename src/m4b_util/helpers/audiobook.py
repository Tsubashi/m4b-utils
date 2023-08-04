from dataclasses import dataclass, field
from pathlib import Path
import shutil
from tempfile import mkdtemp

from natsort import natsorted
from rich import print
from rich.status import Status

from . import cover_utils, ffprobe, ffprogress
from .finders import find_chapters
from .parallel_ffmpeg import ParallelFFmpeg
from .segment_data import SegmentData


@dataclass
class Audiobook:
    """Store all the info pertaining to an audiobook."""
    author: str = None
    chapters: list = field(default_factory=lambda: [])
    cover: str = None
    date: str = None
    output_name: str = None
    title: str = None
    keep_temp_files: bool = False
    _tmp_dir: Path = field(init=False, repr=False, default=None)

    @property
    def _tmp_path(self):
        """Only create our temporary directory if we need it."""
        if not self._tmp_dir:
            self._tmp_dir = Path(mkdtemp(suffix="m4b"))
        if not self._tmp_dir.exists():
            self._tmp_dir.mkdir()
        return self._tmp_dir

    @property
    def suggested_file_name(self):
        """Calculate output name based on what we currently know."""
        # Use a default is self.output_name is not set.
        name = self.output_name or f"{self.author} - {self.title}.m4b"

        # Remove non-allowed file characters
        new_name = ""
        for char in name:
            if (char.isalnum() or char in "._- "):
                new_name += char
            else:
                new_name += "_"
        name = new_name

        # Make sure it ends with .m4b
        if not name.endswith(".m4b"):
            name = f"{name}.m4b"
        return name

    @property
    def metadata(self):
        """Generate the metadata text when requested, since it depends on the current state of the object."""
        # Start by writing the global header
        metadata = (";FFMETADATA1\n"
                    "major_brand=M4A\n"
                    "minor_version=512\n"
                    "compatible_brands=M4A isomiso2\n"
                    f"title={self.title}\n"
                    f"artist={self.author}\n"
                    f"album={self.title}\n"
                    f"date={self.date}\n"
                    "genre=Audiobook\n"
                    )
        # Then add chapters to metadata
        for chapter in self.chapters:
            title = chapter.title
            # Convert times to miliseconds
            start = int(chapter.start_time * 1000)
            end = int(chapter.end_time * 1000)
            metadata += ("[CHAPTER]\n"
                         "TIMEBASE=1/1000\n"
                         f"START={start}\n"
                         f"END={end}\n"
                         f"title={title}\n"
                         )
        return metadata

    @staticmethod
    def scan_dir(input_dir):
        """Scan a directory for files."""
        return natsorted(Path(input_dir).glob("*"))

    def add_chapters_from_chaptered_file(self, input_path):
        """Add chapters from a single file."""
        # Read the new chapters, shifting the times forward to match any segments we already have.
        time_shift = 0.0
        id_shift = 0
        if self.chapters:
            time_shift = self.chapters[-1].end_time
            id_shift = self.chapters[-1].id + 1
        new_chapters = find_chapters(input_path)
        for chapter in new_chapters:
            chapter.start_time = chapter.start_time + time_shift
            chapter.end_time = chapter.end_time + time_shift
            chapter.id = chapter.id + id_shift

        self.chapters.extend(new_chapters)
        # Run ffprobe and parse the output.
        probe = ffprobe.run_probe(input_path)
        if not probe or probe.audio is None:
            print(f"[bold yellow]Warning:[/] Unable to parse '[bold white]{input_path}[/]'. Skipping.")
            return

        # Attempt to fill any missing metadata
        if probe.tags:  # pragma: no branch - None of our test files hit this, but some other audio formats might.
            self.title = self.title or probe.tags.get('title')
            self.author = self.author or probe.tags.get('artist')
            self.date = self.date or probe.tags.get('date')

    def add_chapters_from_directory(self, input_dir, use_filenames=False, decode_durations=False):
        """Read files from a directory that represents an audiobook.

        :param input_dir: Directory to scan.
        :param use_filenames: Use filenames as chapter titles, instead of embedded metadata.
        :param decode_durations: Find duration by fully decoding file, instead of relying on metadata.
        """
        return self.add_chapters_from_filelist(self.scan_dir(input_dir), use_filenames, decode_durations)

    def add_chapters_from_filelist(self, input_files, use_filenames=False, decode_durations=False):
        """Read files from a list of files that represent an audiobook.

        :param input_files: Directory to scan.
        :param use_filenames: Use filenames as chapter titles, instead of embedded metadata.
        :param decode_durations: Find duration by fully decoding file, instead of relying on metadata.
        """
        # Set up variables
        time_counter = 0.0
        if self.chapters:  # If we already have chapters, add these on to the end.
            time_counter = self.chapters[-1].end_time
        segment_counter = len(self.chapters)

        # Start our status tracker
        print("[cyan]Collecting file data...[/]")
        file_scan_status = Status("Starting")
        file_scan_status.start()

        # Scan all the files
        for file in input_files:
            file_scan_status.update(f"Scanning {file.name}")

            # Check for cover file
            if file.stem == "cover" and file.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                self.cover = file
                continue

            # Run ffprobe and parse the output.
            probe = ffprobe.run_probe(file)
            if not probe or probe.audio is None:
                print(f"[bold yellow]Warning:[/] Unable to parse '[bold white]{file}[/]'. Skipping.")
                continue

            # Count which segment we are on. Used in case the chapter has no title.
            segment_counter += 1

            # Attempt to fill any missing metadata
            chapter_title = None
            if probe.tags:  # pragma: no branch - None of our test files hit this, but some other audio formats might.
                self.title = self.title or probe.tags.get('album')
                self.author = self.author or probe.tags.get('artist')
                self.date = self.date or probe.tags.get('date')
                chapter_title = probe.tags.get('title')

            if use_filenames:
                chapter_title = file.stem
            if not chapter_title:
                chapter_title = str(segment_counter)

            # Get the duration, and calculate start/end times.
            start_time = time_counter
            try:
                duration = ffprobe.get_file_duration(file, decode_durations)
            except RuntimeError:
                print(f"[yellow]Warning:[/] Failed to determine duration of '[bold white]{file}[/]'. Ignoring.")
                continue
            time_counter += duration  # Update for next iteration
            end_time = time_counter

            # Record the chapter
            self.chapters.append(SegmentData(
                id=segment_counter,
                title=chapter_title,
                start_time=start_time,
                end_time=end_time,
                backing_file=file
            ))

        # Shut off the status tracker and alert the user
        file_scan_status.stop()
        print("[green]File scan complete.")

    def bind(self, output_path):
        """Bind together an audiobook, based on what we know."""
        if self.keep_temp_files:
            print(f"[yellow]Info:[/] Temp files can be found at [yellow]{self._tmp_path}[/]")

        # Make sure we have at least one chapter.
        if len(self.chapters) == 0:
            print("[bold red]Error:[/] Nothing to bind.")
            return False

        # Determine if we need to bind multiple files, or just rewrite the metadata of a single file.
        first_file = None
        unaccounted_duration = 999  # Will be overwritten, but set to a positive number just in case.
        for segment in self.chapters:
            if segment.backing_file is None:
                s_id = segment.id or ""
                print(f"[yellow]Info:[/] Segment {s_id}: '{segment.title}' does not point to a file.")
                print("[bold red]Error:[/] Cannot bind a non-backed segment.")
                return False

            # Keep info on the first file we see
            if not first_file:
                first_file = segment.backing_file
                unaccounted_duration = ffprobe.get_file_duration(first_file)

            # If we see a file different from the first one, switch to multi-segment bind mode
            if segment.backing_file != first_file:
                return self._bind_multiple_segments(output_path)

            # Subtract this file's duration from our unaccounted_duration metric
            unaccounted_duration = unaccounted_duration - (segment.end_time - segment.start_time)

        # Check to see if we accounted for the total duration of the file. If not, we must be using only part of the
        # original file, and will need to switch to multi-segment bind.
        if unaccounted_duration > 0.1:
            return self._bind_multiple_segments(output_path)

        # If our segments cover the entirety of a single file, we can assume we just need to rewrite the metadata.
        out_file = self._add_chapter_info(first_file)
        return self._finish_bind(out_file, output_path)

    def _bind_multiple_segments(self, output_path):
        # First, convert all audios to m4a, in parallel.
        p = ParallelFFmpeg("Converting files to m4a")
        tasks = list()
        temp_files = list()
        finished_file = self._tmp_path / "finished.m4b"
        for i, segment in enumerate(self.chapters):
            file = segment.backing_file
            # Determine what to call the output file
            out_m4a = self._tmp_path / f"{i}_{file.stem}.m4a"

            # Record the file for concatenation later
            temp_files.append(out_m4a)

            # Write the FFMPEG command
            cmd = ["ffmpeg"]
            if segment.file_start_time:
                cmd.extend(["-ss", str(segment.file_start_time)])
            cmd.extend(["-i", file])
            if segment.file_end_time:
                start_time = segment.file_start_time or 0.0
                end_time_dur = segment.file_end_time - start_time
                cmd.extend(["-t", str(end_time_dur)])
            if segment.title:
                cmd.extend(["-metadata", f"title={segment.title}"])
            cmd.extend(["-filter_complex", "[0:a]asetpts=N/SR/TB[s0]", "-map", "[s0]",
                        "-c:a", "aac", out_m4a, "-y"])
            tasks.append({
                "name": file.stem,
                "command": cmd
            })
        p.process(tasks)

        # Save our original chapter info, so we can restore it later.
        old_chapters = self.chapters
        # Scan the files we just converted, to make sure the metadata matches
        self.chapters = list()
        self.add_chapters_from_filelist(temp_files)

        # Next, concatenate those m4a files into an m4b
        long_file = self._concatenate_files(temp_files)

        # Now, add chapter info
        coverless_file = self._add_chapter_info(long_file)

        # Restore the old chapter list, as we are done writing metadata
        self.chapters = old_chapters

        # Add cover artwork if specified, otherwise just copy the previous output
        if self.cover:
            covered_file = self._tmp_path / "covered.m4b"
            try:
                cover_utils.add_cover(coverless_file, self.cover, covered_file)
            except RuntimeError as e:
                print(str(e))
                exit(1)
            shutil.move(covered_file, finished_file)
        else:
            shutil.move(coverless_file, finished_file)

        return self._finish_bind(finished_file, output_path)

    def _finish_bind(self, input_path, output_path):
        """Copy the output and cleanup."""
        # Copy the output into place
        print("[cyan]Copying output.")
        shutil.copy(input_path, output_path)

        # Clean up
        if not self.keep_temp_files:
            shutil.rmtree(self._tmp_path)

        return True

    def _concatenate_files(self, input_list):
        """Bring all the input files, now m4a, and put them into an m4b."""
        # Start by writing the filelist to a temp file.
        filelist_file = self._tmp_path / "filelist"
        with open(filelist_file, 'w') as f:
            for file in input_list:
                # Single quotes in filenames need to be replaced with `'\''` to work with ffmpeg
                # https://superuser.com/questions/787064/filename-quoting-in-ffmpeg-concat
                safer_filename = str(file).replace("'", "'\\''")
                f.write(f"file '{safer_filename}'\n")

        # Then use that file to concatenate everything.
        output_file = self._tmp_path / "long.m4a"
        cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", filelist_file, "-c", "copy", output_file]
        self._run_ffmpeg(cmd, "Combining Audio Files.")

        return output_file

    def _add_chapter_info(self, input_file):
        """Add chapter info to an m4b file."""
        # Write the metadata to a temp file.
        metadata_file = self._tmp_path / "ffmetadata"
        with open(metadata_file, 'w') as f:
            print(self.metadata, file=f)

        output_file = self._tmp_path / "coverless.m4b"
        cmd = ["ffmpeg", "-y", "-i", input_file, "-i", metadata_file, "-map_metadata", "1", "-map_chapters", "1",
               "-c", "copy", output_file]
        self._run_ffmpeg(cmd, "Converting to .m4b")

        return output_file

    def _run_ffmpeg(self, cmd, message):
        if not ffprogress.run(cmd, message):
            print("[bold red]Error:[/] ffmpeg failed.")
            if not self.keep_temp_files:
                shutil.rmtree(self._tmp_path)
            exit(1)
