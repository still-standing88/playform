from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime
from typing import Callable, Optional

from media_core.ffmpeg import FFmpeg, FFmpegError, Progress
from media_core.ffmpeg.format_capabilities import build_ffmpeg_output_options, get_format, get_container_from_format
from media_core.ffmpeg.effects_catalog import get_effect

_ANALYSIS_PATTERNS = {
    "max_volume": re.compile(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB"),
    "mean_volume": re.compile(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB"),
    "track_gain": re.compile(r"track_gain\s*=\s*(-?\d+(?:\.\d+)?)\s*dB"),
}


def resolve_files_from_entries(entries) -> list:
    resolved = []
    for path, entry_type, entry_formats in entries:
        if entry_type == "file":
            resolved.append((path, None))
            continue

        if entry_type == "folder":
            extensions = set(entry_formats or [])
            try:
                for item in sorted(os.listdir(path)):
                    full_path = os.path.join(path, item)
                    if not os.path.isfile(full_path):
                        continue
                    ext = os.path.splitext(item)[1].lstrip(".").lower()
                    if not extensions or ext in extensions:
                        resolved.append((full_path, path))
            except OSError:
                continue

    return resolved


def probe_sample_rate(ffprobe_executable: str, path: str, default: int = 44100) -> int:
    try:
        ffprobe = FFmpeg(executable=ffprobe_executable)
        ffprobe.option("v", "quiet")
        ffprobe.option("print_format", "json")
        ffprobe.option("show_streams")
        ffprobe.input(path)
        output = ffprobe.execute()
        data = json.loads(output) if output else {}
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "audio" and stream.get("sample_rate"):
                return int(stream["sample_rate"])
    except Exception:
        pass
    return default


class ConversionRunner:
    """Framework-agnostic batch-conversion engine.

    Reports progress through plain callbacks instead of Qt signals so it can be
    driven from a QThread wrapper (see `tools.ffmpeg.batch_converter.job`), a
    script, or a test — without depending on Qt or any app-config module.
    """

    def __init__(
        self,
        entries,
        convert_options: dict,
        processing_effects: list,
        destination_options: dict,
        ffmpeg_executable: str = "ffmpeg",
        ffprobe_executable: str = "ffprobe",
        on_overall_progress: Optional[Callable[[int, int, str], None]] = None,
        on_file_progress: Optional[Callable[[str], None]] = None,
        on_file_completed: Optional[Callable[[str, bool, str], None]] = None,
        on_log_line: Optional[Callable[[str], None]] = None,
    ):
        self.entries = list(entries)
        self.convert_options = convert_options
        self.processing_effects = processing_effects
        self.destination_options = destination_options
        self.ffmpeg_executable = ffmpeg_executable
        self.ffprobe_executable = ffprobe_executable

        self._on_overall_progress = on_overall_progress or (lambda *a: None)
        self._on_file_progress = on_file_progress or (lambda *a: None)
        self._on_file_completed = on_file_completed or (lambda *a: None)
        self._on_log_line = on_log_line or (lambda *a: None)

        self._is_running = True
        self._resume_event = threading.Event()
        self._resume_event.set()

    def stop(self):
        self._is_running = False
        self._resume_event.set()

    def pause(self):
        self._resume_event.clear()

    def resume(self):
        self._resume_event.set()

    def is_paused(self) -> bool:
        return not self._resume_event.is_set()

    def run(self) -> bool:
        """Run the whole batch synchronously (blocking).

        Returns True if every file was processed, False if the run was stopped
        early (`stop()` was called mid-batch).
        """
        files = resolve_files_from_entries(self.entries)
        total = len(files)
        log_lines = []

        for index, (input_path, source_root) in enumerate(files):
            if not self._is_running:
                break

            self._resume_event.wait()
            if not self._is_running:
                break

            base_name = os.path.splitext(os.path.basename(input_path))[0]
            self._on_overall_progress(index, total, base_name)

            try:
                output_path = self._resolve_output_path(input_path, source_root)
                if output_path is None:
                    continue

                if os.path.normcase(os.path.normpath(output_path)) == os.path.normcase(os.path.normpath(input_path)):
                    message = (
                        f"Skipped (output format matches source format, so output would overwrite "
                        f"the source file): {input_path}"
                    )
                    log_lines.append(message)
                    self._on_file_completed(input_path, True, message)
                    continue

                if os.path.exists(output_path) and not self.destination_options.get("overwrite_existing"):
                    message = f"Skipped (exists): {output_path}"
                    log_lines.append(message)
                    self._on_file_completed(input_path, True, message)
                    continue

                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                self._convert_one(input_path, output_path)

                if self.destination_options.get("delete_originals"):
                    try:
                        os.remove(input_path)
                    except OSError as delete_error:
                        log_lines.append(f"Could not delete original {input_path}: {delete_error}")

                message = f"OK: {input_path} -> {output_path}"
                log_lines.append(message)
                self._on_file_completed(input_path, True, message)

            except FFmpegError as error:
                message = f"FAILED: {input_path}: {error.message}"
                log_lines.append(message)
                self._on_file_completed(input_path, False, error.message)
            except Exception as error:
                message = f"FAILED: {input_path}: {error}"
                log_lines.append(message)
                self._on_file_completed(input_path, False, str(error))

        if self.destination_options.get("create_log_file") and self.destination_options.get("log_file_path"):
            self._write_log(log_lines)

        completed = self._is_running
        if completed:
            self._on_overall_progress(total, total, "")
        return completed

    def _resolve_output_path(self, input_path: str, source_root: str):
        base_name = os.path.splitext(os.path.basename(input_path))[0]

        if self.convert_options.get("mode") == "video":
            extension = get_container_from_format(self.convert_options.get("format_label", ""))
        else:
            fmt = get_format(self.convert_options.get("format_id"))
            extension = f".{fmt.extension}"

        if self.destination_options.get("store_in_original_folder"):
            return os.path.join(os.path.dirname(input_path), f"{base_name}{extension}")

        target_folder = self.destination_options.get("target_folder")
        if not target_folder:
            return None

        if self.destination_options.get("preserve_subfolders") and source_root:
            relative_dir = os.path.relpath(os.path.dirname(input_path), os.path.dirname(source_root))
            return os.path.join(target_folder, relative_dir, f"{base_name}{extension}")

        return os.path.join(target_folder, f"{base_name}{extension}")

    def _run_analysis_pass(self, input_path: str, analysis_kind: str) -> float:
        ffmpeg = FFmpeg(executable=self.ffmpeg_executable).option("y")
        analysis_filter = "replaygain" if analysis_kind == "track_gain" else "volumedetect"
        ffmpeg.input(input_path).output("-", **{"af": analysis_filter, "f": "null"})

        captured = []

        @ffmpeg.on("stderr")
        def _on_stderr(line: str):
            captured.append(line)
            self._on_log_line(line)

        try:
            ffmpeg.execute()
        except FFmpegError:
            pass

        pattern = _ANALYSIS_PATTERNS[analysis_kind]
        for line in captured:
            match = pattern.search(line)
            if match:
                return float(match.group(1))
        return 0.0

    def _build_audio_filter_chain(self, input_path: str):
        stages = []
        secondary_input = None
        secondary_options = {}

        for effect_id, values in self.processing_effects:
            effect = get_effect(effect_id)
            resolved_values = dict(values)

            if effect.needs_analysis_pass:
                resolved_values["_measured_db"] = self._run_analysis_pass(input_path, effect.needs_analysis_pass)

            if effect_id == "pitch_no_speed":
                resolved_values["_source_sample_rate"] = probe_sample_rate(self.ffprobe_executable, input_path)

            if effect.needs_secondary_input:
                secondary_input = resolved_values.get("impulse_response_path")
                secondary_options = {
                    "dry": resolved_values.get("dry", 1.0),
                    "wet": resolved_values.get("wet", 1.0),
                }
                continue

            stages.append(effect.build_filter(resolved_values))

        return stages, secondary_input, secondary_options

    def _convert_one(self, input_path: str, output_path: str):
        ffmpeg = FFmpeg(executable=self.ffmpeg_executable).option("y")
        stages, secondary_input, secondary_options = self._build_audio_filter_chain(input_path)

        if self.convert_options.get("mode") == "video":
            self._apply_video_options(ffmpeg, input_path, output_path, stages)
        else:
            self._apply_audio_options(ffmpeg, input_path, output_path, stages, secondary_input, secondary_options)

        @ffmpeg.on("progress")
        def _on_progress(progress: Progress):
            self._on_file_progress(f"Time: {progress.time}, Speed: {progress.speed:.2f}x")

        @ffmpeg.on("stderr")
        def _on_stderr(line: str):
            self._on_log_line(line)

        ffmpeg.execute()

    def _apply_audio_options(self, ffmpeg, input_path, output_path, stages, secondary_input, secondary_options):
        options = self.convert_options
        output_kwargs = build_ffmpeg_output_options(
            options.get("format_id"),
            sample_rate=options.get("sample_rate"),
            bit_depth=options.get("bit_depth"),
            bitrate_kbps=options.get("bit_rate_kbps"),
            vbr_quality=options.get("vbr_quality"),
            codec_option_values=options.get("codec_option_values"),
        )

        if secondary_input:
            ffmpeg.input(input_path)
            ffmpeg.input(secondary_input)
            pre_chain = ",".join(stages) if stages else "anull"
            dry = secondary_options.get("dry", 1.0)
            wet = secondary_options.get("wet", 1.0)
            filter_complex = f"[0:a]{pre_chain}[pre];[pre][1:a]afir=dry={dry}:wet={wet}[aout]"
            ffmpeg.option("filter_complex", filter_complex)
            output_kwargs["map"] = "[aout]"
            ffmpeg.output(output_path, **output_kwargs)
        else:
            if stages:
                output_kwargs["af"] = ",".join(stages)
            ffmpeg.input(input_path).output(output_path, **output_kwargs)

    def _apply_video_options(self, ffmpeg, input_path, output_path, stages):
        options = self.convert_options
        output_kwargs = {"c:v": options.get("codec")}

        if options.get("resolution"):
            output_kwargs["s"] = options["resolution"]
        if options.get("video_bit_rate"):
            output_kwargs["b:v"] = options["video_bit_rate"]
        if options.get("framerate"):
            output_kwargs["r"] = options["framerate"]
        if stages:
            output_kwargs["af"] = ",".join(stages)

        ffmpeg.input(input_path).output(output_path, **output_kwargs)

    def _write_log(self, lines: list):
        log_path = self.destination_options.get("log_file_path")
        try:
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(f"--- Batch Converter run {datetime.now().isoformat()} ---\n")
                for line in lines:
                    handle.write(line + "\n")
        except OSError:
            pass
