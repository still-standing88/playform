import importlib

_LAZY_TOOL_UIS = {
    "BatchConverterUI": "tools.ffmpeg.batch_converter.ui",
    "ExtractorUI": "tools.ffmpeg.media_extractor.ui",
    "TagEditorUI": "tools.tag_editor.ui",
    "ThumbnailGeneratorUI": "tools.ffmpeg.thumbnail_generator.ui",
    "SubtitleConverterUI": "tools.subtitles.converter_ui",
    "SubtitleEditorUI": "tools.subtitles.editor_ui",
    "SpeechConverterUI": "tools.speech_converter.ui",
    "AudiobookToolsUI": "tools.m4b_tools.audiobook_tools.ui",
    "AudiobookCombinerUI": "tools.m4b_tools.combiner.ui",
}

__all__ = list(_LAZY_TOOL_UIS)


def __getattr__(name):
    module_path = _LAZY_TOOL_UIS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(module_path), name)
    globals()[name] = value
    return value
