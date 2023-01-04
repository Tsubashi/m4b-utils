m4b-util
---------
A command line utility for creating, editing, and generally working with m4b files.

## Sub-commands
This application is split into a number of subcommands which can be run from the main command. For a list of available 
commands, run `m4b-util --help`. For details on a specific sub-command, run `m4b-util <command> --help`.

### Bind
The `bind` sub-command is designed to take a folder of audio files and convert them to a single m4b, treating each 
individual file as its own chapter. It can get chapter names from the original files' metadata, original files' names,
from command line arguments, or just number them sequentially. By default, it only scans for mp3 files, but any file 
extension can be added via arguments.

**Example:**
```shell
$ m4b-util bind /path/to/inputs  --title "My Book" --cover /path/to/cover.png -e m4a -e .mp4 --output-dir /path/to/output 
```

### Cover
The `cover` command adds and extracts cover images.

**Example:**
```shell
$ m4b-util cover /path/to/book.m4b --extract /path/to/old/cover.png --apply-cover /path/to/new/cover.png
```

### Labels
The `labels` command converts between Audacity labels, FFMPEG metadata, and Audiobook chapter metadata. Label end times 
are ignored, as audiobooks need contiguous, non-overlapping chapters. When converting from a label file, the end time 
of each segment is set from the start time of the next segment.

**Example:**
```shell
$ m4b-util labels --from-label-file /path/to/labels.txt --to-book /path/to/existing/book.m4b --to-metadata-file /path/to/new_labels.txt
```

### Slide
The `slide` command moves all chapters in a file by a specified duration, keeping the start and end times the same. 
It can optionally trim audio from the start of the file, shifting all chapters an equal amount.

**Example:**
```shell
$ m4b-util slide /path/to/input.mp3 --duration 5.1 --trim-start 2.5
```

### Split 
The `split` command takes a mode and a single audio file input, scans for silence or chapters (depending on mode), 
and writes out individual files containing the audio in-between.

**Example:**
```shell
$ m4b-util split silence /path/to/input.mp3 --output-dir /path/to/output --output_pattern "chapter_{:03d}.mp3"
```
