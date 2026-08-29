import os

title_lngs ={
  "en-US": "English (United States)",
  "en-GB": "English (United Kingdom)",
  "fr-FR": "French (France)",
  "es-ES": "Spanish (Spain)",
  "de-DE": "German (Germany)",
  "it-IT": "Italian (Italy)",
  "pt-PT": "Portuguese (Portugal)",
  "pt-BR": "Portuguese (Brazil)",
  "ru-RU": "Russian (Russia)",
  "zh-CN": "Chinese (Simplified, China)",
  "zh-TW": "Chinese (Traditional, Taiwan)",
  "ja-JP": "Japanese (Japan)",
  "ko-KR": "Korean (South Korea)",
  "ar-SA": "Arabic (Saudi Arabia)",
  "hi-IN": "Hindi (India)",
  "he-IL": "Hebrew (Israel)",
  "nl-NL": "Dutch (Netherlands)",
  "sv-SE": "Swedish (Sweden)",
  "da-DK": "Danish (Denmark)",
  "fi-FI": "Finnish (Finland)",
  "no-NO": "Norwegian (Norway)",
  "pl-PL": "Polish (Poland)",
  "tr-TR": "Turkish (Turkey)",
  "cs-CZ": "Czech (Czech Republic)",
  "el-GR": "Greek (Greece)",
  "hu-HU": "Hungarian (Hungary)",
  "ro-RO": "Romanian (Romania)",
  "sk-SK": "Slovak (Slovakia)",
  "uk-UA": "Ukrainian (Ukraine)",
  "vi-VN": "Vietnamese (Vietnam)"
}

video_resolutions = {
    "X600-480": {"width": 600, "height": 480},
    "X800-600": {"width": 800, "height": 600},
    "X1024-720": {"width": 1024, "height": 720},
    "X1280-720": {"width": 1280, "height": 720},
    "X1280-800": {"width": 1280, "height": 800},
    "X1600-900": {"width": 1600, "height": 900},
    "X1920-1080": {"width": 1920, "height": 1080},
}

video_speeds = [0.25, 0.50, 0.75, 1.0,1.25, 1.5,1.75,2.0,2.5,3.0]

video_rotations = [0, 90, 180, 270]

video_aspect_ratios = [
    "16:9",
    "4:3",
    "1:1",
    "16:10",
    "5:4",
    "21:9",
    "32:9",
    "2.35:1",
    "2.39:1",
]

video_scales = [
    "0.25",
    "0.5",
    "1",
    "1.5",
    "2",
    "2.5",
    "3",
    "4",
    "5"
]

screenshot_formats = ["jpg", "png", "tiff"]
app_languages = ["EN - English", "FR - French", "AR - Arabic", "ES - Spanish"]

# Video quality/decode options for the player's More Options > Video Quality
# submenu. Each list is (label, mpv value); values verified accepted by the
# bundled libmpv build, so an unlisted one means that build rejects it.
video_hwdec_modes = [
    ("Automatic (safe)", "auto-safe"),
    ("Automatic (any)", "auto"),
    ("Disabled", "no"),
    ("D3D11 VA", "d3d11va"),
    ("DXVA2", "dxva2"),
    ("NVDEC", "nvdec"),
    ("Vulkan", "vulkan"),
]

video_scalers = [
    ("Bilinear (fastest)", "bilinear"),
    ("Spline36", "spline36"),
    ("Lanczos", "lanczos"),
    ("EWA Lanczos Sharp (best)", "ewa_lanczossharp"),
    ("Nearest neighbour", "nearest"),
]

video_downscalers = [
    ("Mitchell", "mitchell"),
    ("Bilinear", "bilinear"),
    ("Catmull-Rom", "catmull_rom"),
]

video_interpolation_scalers = [
    ("Oversample", "oversample"),
    ("Mitchell", "mitchell"),
    ("Linear", "linear"),
]

video_framedrop_modes = [
    ("Disabled", "no"),
    ("Output only", "vo"),
    ("Decoder only", "decoder"),
    ("Decoder and output", "decoder+vo"),
]

video_tone_mapping_modes = [
    ("Automatic", "auto"),
    ("BT.2390", "bt.2390"),
    ("Reinhard", "reinhard"),
    ("Hable", "hable"),
    ("Mobius", "mobius"),
    ("Clip", "clip"),
    ("Spline", "spline"),
]

video_sync_modes = [
    ("Audio clock", "audio"),
    ("Display (resample audio)", "display-resample"),
    ("Display (drop frames)", "display-vdrop"),
    ("Desynchronized", "desync"),
]

# How mpv treats an ASS/SSA subtitle's own embedded styling. Without "force",
# the app's font/colour/size settings are ignored for those formats.
subtitle_ass_override_modes = [
    ("Keep subtitle styling, scale only", "scale"),
    ("Keep subtitle styling", "no"),
    ("Override with app settings", "force"),
    ("Override, keeping positions", "yes"),
    ("Strip all styling", "strip"),
]
