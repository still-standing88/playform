from typing import Any, Dict

from .__AV_Common import *


class VideoFilter(AVFilter):


    def __init__(self, media_backend: AVMediaBackend, filter_handle: str, parameters: dict[str, int | float | str], backend_additional_info: dict[Any, Any]):
        filter_type = AVFilterType.AV_TYPE_VIDEO
        super().__init__(filter_type, media_backend, filter_handle, parameters, backend_additional_info)
