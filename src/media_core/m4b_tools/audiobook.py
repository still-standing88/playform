from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import mkdtemp
from typing import Callable, Optional

from media_core.ffmpeg import FFmpeg
from media_core.ffmpeg.errors import FFmpegError

from media_core.m4b_tools import cover as cover_module
from media_core.m4b_tools import ffmetadata
from media_core.m4b_tools import probe as probe_module
from media_core.m4b_tools.finders import find_chapters
from media_core.m4b_tools.naming import natural_sort_key
from media_core.m4b_tools.segment import Segment

_COVER_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def _noop_log(_line: str) -> None:
    return None


def _noop_progress(_name: str) -> None:
    return None


def _always_continue() -> bool:
    return True


@dataclass
class Audiobook:
    """An in-progress audiobook: its metadata plus the chapter segments backing it.

    Framework-agnostic like `media_core.ffmpeg.conversion_job.ConversionRunner`: progress
    and log lines are reported through plain callbacks instead of printing, and long-running
    work checks `should_continue()` between chapters so a caller (see `bind.BindRunner`) can
    support pause/cancel without this class knowing anything about threads or Qt.
    """

    author: Optional[str] = None
    bitrate: str = "128k"
    chapters: list = field(default_factory=list)
    cover: Optional[Path] = None
    date: Optional[str] = None
    narrator: Optional[str] = None
    genre: str = "Audiobook"
    description: Optional[str] = None
    output_name: Optional[str] = None
    title: Optional[str] = None
    keep_temp_files: bool = False

    ffmpeg_executable: str = "ffmpeg"
    ffprobe_executable: str = "ffprobe"

    on_log_line: Callable[[str], None] = field(default=_noop_log, repr=False, compare=False)
    on_file_progress: Callable[[str], None] = field(default=_noop_progress, repr=False, compare=False)
    should_continue: Callable[[], bool] = field(default=_always_continue, repr=False, compare=False)

    _tmp_dir: Optional[Path] = field(init=False, repr=False, default=None, compare=False)

    @property
    def _tmp_path(self) -> Path:
        """Only create the temp directory once something actually needs it."""
        if not self._tmp_dir:
            self._tmp_dir = Path(mkdtemp(suffix="m4b"))
        if not self._tmp_dir.exists():
            self._tmp_dir.mkdir()
        return self._tmp_dir

    @property
    def suggested_file_name(self) -> str:
        name = self.output_name or f"{self.author} - {self.title}.m4b"
        if not name.endswith(".m4b"):
            name = f"{name}.m4b"
        return name

    @property
    def metadata(self) -> str:
        """FFMETADATA1 text describing this audiobook, generated on demand from current state."""
        global_fields = {
            "title": self.title,
            "artist": self.author,
            "album": self.title,
            "album_artist": self.author,
            "composer": self.narrator,
            "date": self.date,
            "genre": self.genre,
            "comment": self.description,
        }
        return ffmetadata.build_ffmetadata(global_fields, self.chapters)

    @metadata.setter
    def metadata(self, value: str):
        global_fields, chapters = ffmetadata.parse_ffmetadata(value)
        self.title = self.title or global_fields.get("title")
        self.author = self.author or global_fields.get("artist")
        self.date = self.date or global_fields.get("date")
        self.chapters.extend(chapters)

    @staticmethod
    def scan_dir(input_dir) -> list[Path]:
        """Scan a directory for files, in natural (numeric-aware) sort order."""
        return sorted(Path(input_dir).glob("*"), key=lambda p: natural_sort_key(p.name))

    def add_chapters_from_chaptered_file(self, input_path):
        """Add chapters read from a single already-chaptered file (e.g. an existing m4b)."""
        time_shift = 0.0
        id_shift = 0
        if self.chapters:
            time_shift = self.chapters[-1].end_time
            id_shift = (self.chapters[-1].id or 0) + 1

        new_chapters = find_chapters(input_path, ffprobe_executable=self.ffprobe_executable)
        for chapter in new_chapters:
            chapter.start_time += time_shift
            chapter.end_time += time_shift
            chapter.id = (chapter.id or 0) + id_shift
        self.chapters.extend(new_chapters)

        probe = probe_module.run_probe(input_path, self.ffprobe_executable)
        if not probe or probe.audio_stream is None:
            self.on_log_line(f"Warning: Unable to parse '{input_path}'. Skipping.")
            return

        if probe.tags:
            self.title = self.title or probe.tags.get("title")
            self.author = self.author or probe.tags.get("artist")
            self.date = self.date or probe.tags.get("date")

    def add_chapters_from_directory(self, input_dir, use_filenames: bool = False, decode_durations: bool = False):
        """Read files from a directory that represents an audiobook (one chapter per file)."""
        return self.add_chapters_from_filelist(self.scan_dir(input_dir), use_filenames, decode_durations)

    def add_chapters_from_filelist(self, input_files, use_filenames: bool = False, decode_durations: bool = False):
        """Read files from an ordered list that represent an audiobook (one chapter per file)."""
        time_counter = 0.0
        if self.chapters:
            time_counter = self.chapters[-1].end_time
        segment_counter = len(self.chapters)

        for file in input_files:
            file = Path(file)
            self.on_file_progress(f"Scanning {file.name}")

            if file.stem == "cover" and file.suffix.lower() in _COVER_EXTENSIONS:
                self.cover = file
                continue

            probe = probe_module.run_probe(file, self.ffprobe_executable)
            if not probe or probe.audio_stream is None:
                self.on_log_line(f"Warning: Unable to parse '{file}'. Skipping.")
                continue

            segment_counter += 1

            chapter_title = None
            if probe.tags:
                self.title = self.title or probe.tags.get("album")
                self.author = self.author or probe.tags.get("artist")
                self.date = self.date or probe.tags.get("date")
                chapter_title = probe.tags.get("title")

            if use_filenames:
                chapter_title = file.stem
            if not chapter_title:
                chapter_title = str(segment_counter)

            start_time = time_counter
            try:
                duration = probe_module.get_file_duration(
                    file, self.ffprobe_executable, self.ffmpeg_executable, decode_durations
                )
            except RuntimeError:
                self.on_log_line(f"Warning: Failed to determine duration of '{file}'. Ignoring.")
                continue
            time_counter += duration

            self.chapters.append(Segment(
                id=segment_counter,
                title=chapter_title,
                start_time=start_time,
                end_time=time_counter,
                backing_file=file,
            ))

    def bind(self, output_path) -> bool:
        """Bind together an audiobook from what's currently known about it."""
        if self.keep_temp_files:
            self.on_log_line(f"Info: Temp files can be found at {self._tmp_path}")

        if len(self.chapters) == 0:
            self.on_log_line("Error: Nothing to bind.")
            return False

        first_file = None
        unaccounted_duration = 999.0
        for segment in self.chapters:
            if segment.backing_file is None:
                self.on_log_line(f"Error: Segment {segment.id or ''}: '{segment.title}' does not point to a file.")
                return False

            if not first_file:
                first_file = segment.backing_file
                unaccounted_duration = probe_module.get_file_duration(first_file, self.ffprobe_executable)

            if segment.backing_file != first_file:
                return self._bind_multiple_segments(output_path)

            unaccounted_duration -= (segment.end_time - segment.start_time)

        if unaccounted_duration > 0.1:
            return self._bind_multiple_segments(output_path)

        out_file = self._add_chapter_info(first_file)
        if out_file is None:
            return False
        return self._finish_bind(out_file, output_path)

    def _bind_multiple_segments(self, output_path) -> bool:
        temp_files = []
        finished_file = self._tmp_path / "finished.m4b"

        for i, segment in enumerate(self.chapters):
            if not self.should_continue():
                return False

            file = Path(segment.backing_file)
            out_m4a = self._tmp_path / f"{i}_{file.stem}.m4a"
            temp_files.append(out_m4a)

            self.on_file_progress(f"Converting {file.name} to m4a")
            if not self._convert_chapter_to_m4a(file, segment, out_m4a):
                return False

        old_chapters = self.chapters
        self.chapters = []
        self.add_chapters_from_filelist(temp_files)

        long_file = self._concatenate_files(temp_files)
        if long_file is None:
            return False

        coverless_file = self._add_chapter_info(long_file)
        self.chapters = old_chapters
        if coverless_file is None:
            return False

        if self.cover:
            covered_file = self._tmp_path / "covered.m4b"
            try:
                cover_module.add_cover(coverless_file, self.cover, covered_file, self.ffmpeg_executable)
            except FFmpegError as error:
                self.on_log_line(f"Error: Failed to add cover: {error.message}")
                return False
            shutil.move(covered_file, finished_file)
        else:
            shutil.move(coverless_file, finished_file)

        return self._finish_bind(finished_file, output_path)

    def _convert_chapter_to_m4a(self, file: Path, segment: Segment, out_m4a: Path) -> bool:
        ffmpeg = FFmpeg(executable=self.ffmpeg_executable).option("y")
        input_options = {}
        if segment.file_start_time:
            input_options["ss"] = segment.file_start_time
        ffmpeg.input(str(file), input_options)

        output_options = {
            "filter_complex": "[0:a]asetpts=N/SR/TB[s0]",
            "map": "[s0]",
            "c:a": "aac",
            "b:a": self.bitrate,
        }
        if segment.file_end_time:
            start_time = segment.file_start_time or 0.0
            output_options["t"] = segment.file_end_time - start_time
        if segment.title:
            output_options["metadata"] = f"title={segment.title}"

        ffmpeg.output(str(out_m4a), **output_options)
        return self._run(ffmpeg, f"Converting {file.name}")

    def _finish_bind(self, input_path, output_path) -> bool:
        self.on_log_line(f"Copying output to '{output_path}'.")
        shutil.copy(input_path, output_path)
        if not self.keep_temp_files and self._tmp_dir is not None:
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
        return True

    def _concatenate_files(self, input_list: list) -> Optional[Path]:
        filelist_file = self._tmp_path / "filelist"
        with open(filelist_file, "w", encoding="utf-8") as handle:
            for file in input_list:
                # Single quotes in filenames need to be escaped to work with ffmpeg's concat demuxer.
                # https://superuser.com/questions/787064/filename-quoting-in-ffmpeg-concat
                safe_name = str(file).replace("'", "'\\''")
                handle.write(f"file '{safe_name}'\n")

        output_file = self._tmp_path / "long.m4a"
        ffmpeg = FFmpeg(executable=self.ffmpeg_executable).option("y")
        ffmpeg.input(str(filelist_file), **{"f": "concat", "safe": "0"})
        ffmpeg.output(str(output_file), **{"c": "copy"})
        if not self._run(ffmpeg, "Combining audio files"):
            return None
        return output_file

    def _add_chapter_info(self, input_file) -> Optional[Path]:
        metadata_file = self._tmp_path / "ffmetadata"
        with open(metadata_file, "w", encoding="utf-8") as handle:
            handle.write(self.metadata)

        output_file = self._tmp_path / "coverless.m4b"
        ffmpeg = FFmpeg(executable=self.ffmpeg_executable).option("y")
        ffmpeg.input(str(input_file))
        ffmpeg.input(str(metadata_file))
        ffmpeg.output(str(output_file), **{
            "map_metadata": "1",
            "map_chapters": "1",
            "c": "copy",
        })
        if not self._run(ffmpeg, "Writing chapter metadata"):
            return None
        return output_file

    def _run(self, ffmpeg: FFmpeg, message: str) -> bool:
        @ffmpeg.on("stderr")
        def _on_stderr(line: str):
            self.on_log_line(line)

        try:
            ffmpeg.execute()
            return True
        except FFmpegError as error:
            self.on_log_line(f"Error: {message} failed: {error.message}")
            if not self.keep_temp_files and self._tmp_dir is not None:
                shutil.rmtree(self._tmp_dir, ignore_errors=True)
            return False
