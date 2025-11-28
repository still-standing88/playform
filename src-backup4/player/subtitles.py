import os
import cchardet
from pycaption import detect_format, CaptionNode
from pycaption.base import CaptionList
from typing import List, Optional

class SubtitleEntry:

    
    def __init__(self, text: str, start_usec: int, end_usec: int):
        self.text = text
        self.start = start_usec
        self.end = end_usec

class SubtitleManager:


    def __init__(self):
        self.subtitles: List[SubtitleEntry] = []
        self.supported_formats = ["srt", "vtt", "smi", "sami", "scc", "dfxp", "ttml", "sub", "ass"]
        self.current_subtitle_path: Optional[str] = None

    def _find_subtitle_file(self, video_path: str) -> Optional[str]:
        try:
            if not os.path.isfile(video_path):
                return None
            dir_path = os.path.dirname(video_path)
            filename = os.path.splitext(os.path.basename(video_path))[0]
            for fmt in self.supported_formats:
                sub_path = os.path.join(dir_path, f"{filename}.{fmt}")
                if os.path.exists(sub_path):
                    return sub_path
        except Exception:
            pass
        return None

    def _get_encoding(self, path: str) -> str:
        try:
            with open(path, "rb") as fp:
                detection = cchardet.detect(fp.read())
                return detection["encoding"] if detection else 'utf-8'
        except Exception:
            return 'utf-8'

    def load_for_video(self, video_path: str, language: str = 'en-US') -> bool:
        self.clear()
        self.current_subtitle_path = self._find_subtitle_file(video_path)
        if not self.current_subtitle_path:
            return False

        try:
            encoding = self._get_encoding(self.current_subtitle_path)
            with open(self.current_subtitle_path, "r", encoding=encoding, errors='ignore') as f:
                content = f.read()

            reader_class = detect_format(content)
            if not reader_class:
                return False
            
            caption_set = reader_class().read(content)
            
            available_langs = caption_set.get_languages()
            if not available_langs:
                return False

            lang_to_use = language if language in available_langs else available_langs[0]
                
            captions: CaptionList = caption_set.get_captions(lang_to_use)
            
            for caption in captions:
                text = ' '.join([node.content for node in caption.nodes if node.type_ == CaptionNode.TEXT]).strip()
                if text:
                    self.subtitles.append(SubtitleEntry(text.replace('\n', ' '), caption.start, caption.end))
            
            return len(self.subtitles) > 0
        except Exception:
            self.clear()
            return False

    def get_subtitle_at(self, position_usec: int) -> Optional[str]:
        for sub in self.subtitles:
            if sub.start <= position_usec <= sub.end:
                return sub.text
        return None

    def has_subtitles(self) -> bool:
        return bool(self.subtitles)

    def clear(self):
        self.subtitles.clear()
        self.current_subtitle_path = None