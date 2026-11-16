from .mediacap import query
from .models import CaptureDevice, CaptureFormatOption, MediaKind


_DEVICE_LISTS = {
    MediaKind.AUDIO_INPUT: ("audio-input", ("audio", "input")),
    MediaKind.AUDIO_OUTPUT: ("audio-output", ("audio", "output")),
    MediaKind.CAMERA: ("cameras", ("cameras",)),
    MediaKind.MONITOR: ("monitors", ("monitors",)),
    MediaKind.WINDOW: ("windows", ("windows",)),
}


class CaptureCapabilities:
    def __init__(self, executable):
        self.executable = executable

    def inventory(self) -> dict[MediaKind, list[CaptureDevice]]:
        data = query(self.executable, "list", "all", allow_partial=True)
        return {kind: self._devices(kind, data.get(key, [])) for kind, (key, _) in _DEVICE_LISTS.items()}

    def list_devices(self, kind: MediaKind) -> list[CaptureDevice]:
        _, subcommand = _DEVICE_LISTS[kind]
        return self._devices(kind, query(self.executable, "list", *subcommand))

    @staticmethod
    def _devices(kind, rows):
        devices = []
        for row in rows:
            extra = dict(row)
            if kind in (MediaKind.AUDIO_INPUT, MediaKind.AUDIO_OUTPUT):
                ident = row["id"] or f'{row["kind"]}:{row["index"]}'
                name = row["name"]
                extra["route"] = "mic" if kind == MediaKind.AUDIO_INPUT else "system"
                if row["id"]:
                    extra["audio_id"] = row["id"]
                else:
                    extra["route"] = f'{row["kind"]}:{row["index"]}'
            elif kind == MediaKind.CAMERA:
                extra["selector"] = row["index"]
                name = row["name"]
                ident = row["unique_id"] or f'camera:{name}:{row["index"]}'
            elif kind == MediaKind.MONITOR:
                extra["selector"] = row["id"]
                name = row["name"] or f'Display {row["index"] + 1}'
                ident = row["name"] or str(row["id"])
                extra["legacy_id"] = f'{row["x"]},{row["y"]},{row["width"]},{row["height"]}'
            else:
                extra["selector"] = row["handle"]
                ident = str(row["handle"])
                name = row["title"] or f'Window {ident}'
            devices.append(CaptureDevice(kind, ident, name, backend="mediacap", extra=extra))
        return devices

    @staticmethod
    def resolve_device(devices, device_id, device_name=""):
        matches = [d for d in devices if device_id and device_id.casefold() in
                   (d.id.casefold(), str(d.extra.get("legacy_id", "")).casefold())]
        if len(matches) == 1:
            return matches[0]
        names = {name.casefold() for name in (device_name, device_id) if name}
        matches = [d for d in devices if d.name.casefold() in names]
        return matches[0] if len(matches) == 1 else None

    def camera_formats(self, device: CaptureDevice) -> list[CaptureFormatOption]:
        data = query(self.executable, "info", "camera", str(device.extra["selector"]))
        return [CaptureFormatOption(size["width"], size["height"], 0, pixel_format=pixel_format)
                for size in data.get("resolutions", [])
                for pixel_format in data.get("pixel_formats") or [""]]

    def loopback_note(self) -> str:
        return ""

    def window_capture_note(self) -> str:
        return ""

    def screen_capture_note(self) -> str:
        return ""
