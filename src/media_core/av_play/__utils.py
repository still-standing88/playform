import os
import platform
from pathlib import Path
from typing import Union, List, Optional
from ctypes.util import find_library

def find_lib_path(paths: Union[List[str], str], libname: str) -> Optional[str]:
    system = platform.system().lower()
    extensions = {
        'windows': ['.dll'],
        'darwin': ['.dylib', '.so'],
        'linux': ['.so']
    }.get(system, ['.so'])
    
    if isinstance(paths, str):
        paths = [paths]
    
    system_path = find_library(libname)
    if system_path and os.path.exists(system_path):
        return system_path
    
    for base_path in paths:
        path_obj = Path(base_path)
        if path_obj.is_file() and path_obj.name.startswith(libname):
            return str(path_obj)
        
        if path_obj.is_dir():
            for ext in extensions:
                candidates = [
                    f"{libname}{ext}",
                    f"lib{libname}{ext}",
                    f"{libname}.0{ext}",
                    f"lib{libname}.0{ext}"
                ]
                for candidate in candidates:
                    lib_path = path_obj / candidate
                    if lib_path.exists():
                        return str(lib_path)
    
    return None