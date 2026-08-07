import os
import re
from datetime import datetime

from PySide6.QtCore import QThread, Signal

from tools.ffmpeg_handler import FFmpegHandler
from media_core.ffmpeg import FFmpegError, Progress
from tools.ffmpeg.batch_converter.format_capabilities import build_ffmpeg_output_options, get_format
from tools.ffmpeg.batch_converter.effects_catalog import get_effect
from tools.utils import get_video_formats_map, get_container_from_format
from utilities.chapter_probe import get_media_metadata

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


def _probe_sample_rate(path: str, default: int = 44100) -> int:
    try:
        metadata = get_media_metadata(path)
        for stream in metadata.get("streams", []):
            if stream.get("codec_type") == "audio" and stream.get("sample_rate"):
                return int(stream["sample_rate"])
    except Exception:
        pass
    return default


class BatchConverterJob(QThread):
    overall_progress = Signal(int, int, str)
    file_progress = Signal(str)
    file_completed = Signal(str, bool, str)
    log_line = Signal(str)
    finished_all = Signal()

    def __init__(self, entries, convert_options: dict, processing_effects: list, destination_options: dict):
        super().__init__()
        self.entries = list(entries)
        self.convert_options = convert_options
        self.processing_effects = processing_effects
        self.destination_options = destination_options
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        files = resolve_files_from_entries(self.entries)
        total = len(files)
        log_lines = []

        for index, (input_path, source_root) in enumerate(files):
            if not self._is_running:
                break

            base_name = os.path.splitext(os.path.basename(input_path))[0]
            self.overall_progress.emit(index, total, base_name)

            try:
                output_path = self._resolve_output_path(input_path, source_root)
                if output_path is None:
                    continue

                if os.path.exists(output_path) and not self.destination_options.get("overwrite_existing"):
                    message = f"Skipped (exists): {output_path}"
                    log_lines.append(message)
                    self.file_completed.emit(input_path, True, message)
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
                self.file_completed.emit(input_path, True, message)

            except FFmpegError as error:
                message = f"FAILED: {input_path}: {error.message}"
                log_lines.append(message)
                self.file_completed.emit(input_path, False, error.message)
            except Exception as error:
                message = f"FAILED: {input_path}: {error}"
                log_lines.append(message)
                self.file_completed.emit(input_path, False, str(error))

        if self.destination_options.get("create_log_file") and self.destination_options.get("log_file_path"):
            self._write_log(log_lines)

        if self._is_running:
            self.overall_progress.emit(total, total, "")
            self.finished_all.emit()

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
        ffmpeg = FFmpegHandler.create_ffmpeg_instance().option("y")
        analysis_filter = "replaygain" if analysis_kind == "track_gain" else "volumedetect"
        ffmpeg.input(input_path).output("-", **{"af": analysis_filter, "f": "null"})

        captured = []

        @ffmpeg.on("stderr")
        def _on_stderr(line: str):
            captured.append(line)

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
                resolved_values["_source_sample_rate"] = _probe_sample_rate(input_path)

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
        ffmpeg = FFmpegHandler.create_ffmpeg_instance().option("y")
        stages, secondary_input, secondary_options = self._build_audio_filter_chain(input_path)

        if self.convert_options.get("mode") == "video":
            self._apply_video_options(ffmpeg, input_path, output_path, stages)
        else:
            self._apply_audio_options(ffmpeg, input_path, output_path, stages, secondary_input, secondary_options)

        @ffmpeg.on("progress")
        def _on_progress(progress: Progress):
            self.file_progress.emit(
                _("Time: {time}, Speed: {speed:.2f}x").format(time=progress.time, speed=progress.speed)
            )

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
