from __future__ import annotations

import csv
import glob
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from media_core.m4b_tools import probe as probe_module
from media_core.m4b_tools.audiobook import Audiobook
from media_core.m4b_tools.finders import find_chapters
from media_core.m4b_tools.naming import natural_sort_key
from media_core.m4b_tools.runner import M4bToolsRunner
from media_core.m4b_tools.segment import Segment

_COVER_URL_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
_CHAPTER_PREFIX_RE = re.compile(r"^(chapter|ch|part|pt)[\s\-_]*\d*[\s\-_]*", re.IGNORECASE)
_LEADING_NUMBER_RE = re.compile(r"^\d+[\s\-_]*")


def derive_chapter_title(file_path, index: int, existing_title: str = "") -> str:
    """Guess a chapter title from a source file's own metadata, falling back to its filename."""
    if existing_title and existing_title.strip():
        return existing_title.strip()

    cleaned = _CHAPTER_PREFIX_RE.sub("", Path(file_path).stem)
    cleaned = _LEADING_NUMBER_RE.sub("", cleaned)
    cleaned = cleaned.replace("_", " ").replace("-", " ")
    cleaned = " ".join(cleaned.split())
    return cleaned.title() if cleaned else f"Chapter {index}"


def parse_combine_csv(csv_path) -> tuple:
    """Parse a combine CSV: `#key,value` metadata header lines followed by `file,title` rows.

    Returns (entries, metadata) where entries is `[{"file": abs_path, "title": str}, ...]`
    and metadata is the lowercased `#`-line dict (title/author/narrator/genre/year/
    description/output_path/cover_path).
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(csv_path, encoding="utf-8") as handle:
        lines = handle.readlines()

    metadata: dict = {}
    data_start = 0
    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if line.startswith("#"):
            if "," in line:
                key, value = line[1:].split(",", 1)
            elif ":" in line:
                key, value = line[1:].split(":", 1)
            else:
                data_start = index + 1
                continue
            key, value = key.strip().lower(), value.strip()
            if key and value:
                metadata[key] = value
            data_start = index + 1
        elif line:
            break

    data_lines = [line for line in lines[data_start:] if line.strip()]
    if not data_lines:
        raise ValueError("No data rows found in CSV file.")

    entries = []
    for row in csv.DictReader(data_lines):
        file_field = (row.get("file") or "").strip()
        if not file_field:
            continue
        file_path = Path(file_field)
        if not file_path.is_absolute():
            file_path = csv_path.parent / file_path
        entries.append({"file": str(file_path.resolve()), "title": (row.get("title") or "").strip()})

    if not entries:
        raise ValueError("No file rows found in CSV file.")
    return entries, metadata


def _resolve_cover(cover_field: str, csv_dir: Optional[Path], dest_dir: Path,
                    on_log_line: Callable[[str], None]) -> Optional[Path]:
    if cover_field.startswith(("http://", "https://")):
        return _download_cover(cover_field, dest_dir, on_log_line)

    cover_path = Path(cover_field)
    if not cover_path.is_absolute() and csv_dir:
        cover_path = csv_dir / cover_path
    cover_path = cover_path.resolve()
    if cover_path.exists():
        return cover_path
    on_log_line(f"Warning: cover art file not found: {cover_path}")
    return None


def _download_cover(url: str, dest_dir: Path, on_log_line: Callable[[str], None]) -> Optional[Path]:
    ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if ext not in _COVER_URL_EXTENSIONS:
        ext = ".jpg"

    dest_dir.mkdir(parents=True, exist_ok=True)
    output_path = dest_dir / f"cover{ext}"
    try:
        with urllib.request.urlopen(url) as response:  # noqa: S310 - user-supplied CSV cover URL, by design
            output_path.write_bytes(response.read())
    except OSError as error:
        on_log_line(f"Warning: failed to download cover art from {url}: {error}")
        return None

    if output_path.exists() and output_path.stat().st_size > 0:
        return output_path
    return None


class CombineRunner(M4bToolsRunner):
    """Combines several already-bound audiobook files into one, with chapters.

    Reuses `Audiobook.bind()` for all the actual ffmpeg work (re-encoding each source to a
    uniform AAC chapter, concatenating, and writing metadata/cover) - this class only turns
    a CSV/glob/file-list source into the `Segment` list `Audiobook` expects. Mirrors
    `media_core.ffmpeg.conversion_job.ConversionRunner`'s callback shape and threading model.
    """

    def __init__(
        self,
        output_file: Optional[str] = None,
        input_pattern: Optional[str] = None,
        input_files: Optional[list] = None,
        csv_file: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        narrator: Optional[str] = None,
        genre: Optional[str] = None,
        year: Optional[str] = None,
        description: Optional[str] = None,
        cover: Optional[str] = None,
        preserve_existing_chapters: bool = False,
        bitrate: str = "64k",
        keep_temp_files: bool = False,
        ffmpeg_executable: str = "ffmpeg",
        ffprobe_executable: str = "ffprobe",
        on_overall_progress: Optional[Callable[[int, int, str], None]] = None,
        on_file_progress: Optional[Callable[[str], None]] = None,
        on_log_line: Optional[Callable[[str], None]] = None,
    ):
        super().__init__()
        self.output_file = output_file
        self.input_pattern = input_pattern
        self.input_files = input_files
        self.csv_file = csv_file
        self.title = title
        self.author = author
        self.narrator = narrator
        self.genre = genre
        self.year = year
        self.description = description
        self.cover = cover
        self.preserve_existing_chapters = preserve_existing_chapters
        self.bitrate = bitrate
        self.keep_temp_files = keep_temp_files
        self.ffmpeg_executable = ffmpeg_executable
        self.ffprobe_executable = ffprobe_executable

        self._on_overall_progress = on_overall_progress or (lambda *a: None)
        self._on_file_progress = on_file_progress or (lambda *a: None)
        self._on_log_line = on_log_line or (lambda line: None)

    def run(self) -> bool:
        try:
            files, csv_metadata = self._resolve_inputs()
        except (FileNotFoundError, ValueError) as error:
            self._on_log_line(f"Error: {error}")
            return False

        if not files:
            self._on_log_line("Error: No source files to combine.")
            return False

        output_file = self.output_file or csv_metadata.get("output_path")
        if not output_file:
            self._on_log_line("Error: Output file must be specified.")
            return False

        segments = self._build_segments(files)
        if not self._is_running:
            return False
        if not segments:
            self._on_log_line("Error: Could not build any chapters from the source files.")
            return False

        book = Audiobook(
            title=self.title or csv_metadata.get("title") or "Combined Audiobook",
            author=self.author or csv_metadata.get("author"),
            narrator=self.narrator or csv_metadata.get("narrator"),
            genre=self.genre or csv_metadata.get("genre", "Audiobook"),
            date=self.year or csv_metadata.get("year"),
            description=self.description or csv_metadata.get("description"),
            bitrate=self.bitrate,
            keep_temp_files=self.keep_temp_files,
            chapters=segments,
            ffmpeg_executable=self.ffmpeg_executable,
            ffprobe_executable=self.ffprobe_executable,
            on_log_line=self._on_log_line,
            on_file_progress=self._on_file_progress,
            should_continue=self._checkpoint,
        )

        cover_field = self.cover or csv_metadata.get("cover_path")
        if cover_field:
            csv_dir = Path(self.csv_file).parent if self.csv_file else None
            book.cover = _resolve_cover(cover_field, csv_dir, book._tmp_path, self._on_log_line)

        return book.bind(output_file)

    def _resolve_inputs(self) -> tuple:
        if self.csv_file:
            return parse_combine_csv(self.csv_file)

        if self.input_files:
            paths = [Path(f) for f in self.input_files]
        elif self.input_pattern:
            paths = sorted(
                (Path(p) for p in glob.glob(self.input_pattern, recursive=True)
                 if Path(p).suffix.lower() in {".m4b", ".m4a"}),
                key=lambda p: natural_sort_key(p.name),
            )
        else:
            raise ValueError("One of csv_file, input_files, or input_pattern must be provided.")

        return [{"file": str(p.resolve()), "title": ""} for p in paths], {}

    def _build_segments(self, files: list) -> list:
        segments = []
        current_time = 0.0
        total = len(files)

        for index, entry in enumerate(files, start=1):
            if not self._checkpoint():
                break

            file_path = Path(entry["file"])
            self._on_overall_progress(index - 1, total, file_path.name)

            try:
                duration = probe_module.get_file_duration(file_path, self.ffprobe_executable)
            except RuntimeError as error:
                self._on_log_line(f"Warning: {error} Skipping {file_path}.")
                continue

            probe = probe_module.run_probe(file_path, self.ffprobe_executable)
            existing_title = (probe.tags.get("title") if probe and probe.tags else "") or ""
            base_title = entry["title"] or derive_chapter_title(file_path, index, existing_title)

            existing_chapters = (
                find_chapters(file_path, ffprobe_executable=self.ffprobe_executable)
                if self.preserve_existing_chapters else []
            )

            if existing_chapters:
                for chapter in existing_chapters:
                    segments.append(Segment(
                        start_time=current_time + chapter.file_start_time,
                        end_time=current_time + chapter.file_end_time,
                        title=f"{base_title} - {chapter.title}" if chapter.title else base_title,
                        backing_file=file_path,
                        file_start_time=chapter.file_start_time,
                        file_end_time=chapter.file_end_time,
                    ))
            else:
                segments.append(Segment(
                    start_time=current_time,
                    end_time=current_time + duration,
                    title=base_title,
                    backing_file=file_path,
                    file_start_time=0.0,
                    file_end_time=duration,
                ))

            current_time += duration

        for index, segment in enumerate(segments):
            segment.id = index
        self._on_overall_progress(total, total, "")
        return segments
