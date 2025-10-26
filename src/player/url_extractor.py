import os
import logging
from typing import Union, List, Optional
from PySide6.QtCore import QThread, Signal
from app_config import prefs
from .url import extract, is_supported

logger = logging.getLogger(__name__)

class UrlExtractor(QThread):
    started = Signal()
    finished = Signal(object)
    failed = Signal(str)
    
    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        
    def run(self):
        try:
            self.started.emit()
            logger.info(f"Starting URL extraction for: {self.url}")
            
            cookies_path = prefs.prefs.get("youtube_cookies", "")
            cookies = None
            
            if cookies_path and os.path.exists(cookies_path):
                logger.info(f"Using cookies file: {cookies_path}")
                cookies = cookies_path
            else:
                logger.info("No valid cookies file found, proceeding without cookies")
            
            if not is_supported(self.url):
                logger.info(f"URL not supported by extractors, returning as-is: {self.url}")
                self.finished.emit(self.url)
                return
            
            logger.info("Extracting URL(s)...")
            result = extract(self.url, cookies=cookies)
            
            if isinstance(result, list):
                logger.info(f"Extracted playlist with {len(result)} entries")
            else:
                logger.info("Extracted single URL")
                
            self.finished.emit(result)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"URL extraction failed: {error_msg}")
            self.failed.emit(error_msg)
