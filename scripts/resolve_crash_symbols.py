"""One-off: resolve python312.dll+offset crash addresses to actual CPython
function names via Microsoft's public symbol server, using dbghelp.dll's
own symbol engine (it handles the PDB download/parsing/caching itself --
we're just driving SymInitialize/SymFromAddr).

Usage:
    vnv\\Scripts\\python.exe scripts\\resolve_crash_symbols.py 0x278b44 0x81f78 0x919e9
"""
import ctypes
import os
import sys
from ctypes import wintypes

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from utilities.crash_handler import _enum_modules_with_ranges  # noqa: E402

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
dbghelp = ctypes.WinDLL("dbghelp", use_last_error=True)

SYMOPT_UNDNAME = 0x00000002
SYMOPT_DEFERRED_LOADS = 0x00000004
SYMOPT_LOAD_LINES = 0x00000010

MAX_SYM_NAME = 2000


class SYMBOL_INFO(ctypes.Structure):
    _fields_ = [
        ("SizeOfStruct", wintypes.ULONG),
        ("TypeIndex", wintypes.ULONG),
        ("Reserved", ctypes.c_ulonglong * 2),
        ("Index", wintypes.ULONG),
        ("Size", wintypes.ULONG),
        ("ModBase", ctypes.c_ulonglong),
        ("Flags", wintypes.ULONG),
        ("Value", ctypes.c_ulonglong),
        ("Address", ctypes.c_ulonglong),
        ("Register", wintypes.ULONG),
        ("Scope", wintypes.ULONG),
        ("Tag", wintypes.ULONG),
        ("NameLen", wintypes.ULONG),
        ("MaxNameLen", wintypes.ULONG),
        ("Name", ctypes.c_char * MAX_SYM_NAME),
    ]


dbghelp.SymInitializeW.restype = wintypes.BOOL
dbghelp.SymInitializeW.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR, wintypes.BOOL]
dbghelp.SymSetOptions.restype = wintypes.DWORD
dbghelp.SymSetOptions.argtypes = [wintypes.DWORD]
dbghelp.SymLoadModuleExW.restype = ctypes.c_ulonglong
dbghelp.SymLoadModuleExW.argtypes = [
    wintypes.HANDLE, wintypes.HANDLE, wintypes.LPCWSTR, wintypes.LPCWSTR,
    ctypes.c_ulonglong, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
]
dbghelp.SymFromAddr.restype = wintypes.BOOL
dbghelp.SymFromAddr.argtypes = [wintypes.HANDLE, ctypes.c_ulonglong, ctypes.POINTER(ctypes.c_ulonglong), ctypes.POINTER(SYMBOL_INFO)]
dbghelp.SymCleanup.restype = wintypes.BOOL
dbghelp.SymCleanup.argtypes = [wintypes.HANDLE]


def main():
    offsets = [int(a, 16) for a in sys.argv[1:]]
    if not offsets:
        print("usage: resolve_crash_symbols.py 0xOFFSET [0xOFFSET ...]")
        sys.exit(1)

    cache_dir = os.path.join(os.environ.get("TEMP", "."), "symbols_cache")
    os.makedirs(cache_dir, exist_ok=True)
    sym_path = f"srv*{cache_dir}*https://msdl.microsoft.com/download/symbols"

    h_process = kernel32.GetCurrentProcess()
    dbghelp.SymSetOptions(SYMOPT_UNDNAME | SYMOPT_DEFERRED_LOADS | SYMOPT_LOAD_LINES)
    if not dbghelp.SymInitializeW(h_process, sym_path, False):
        print("SymInitializeW failed, GetLastError=", ctypes.get_last_error())
        sys.exit(1)

    python312 = None
    for name, base, size in _enum_modules_with_ranges():
        if name.lower().endswith("python312.dll"):
            python312 = (name, base, size)
            break

    if python312 is None:
        print("python312.dll not found in this process's module list (unexpected)")
        sys.exit(1)

    name, base, size = python312
    print(f"python312.dll base=0x{base:x} size=0x{size:x} path={name}")

    module_base = dbghelp.SymLoadModuleExW(h_process, None, name, None, base, size, None, 0)
    if module_base == 0:
        err = ctypes.get_last_error()
        if err != 0:
            print(f"SymLoadModuleExW failed, GetLastError=0x{err:x}")
            sys.exit(1)
        module_base = base

    print("Fetching/parsing symbols from Microsoft symbol server (first run can take a while)...")

    for offset in offsets:
        address = base + offset
        buf = ctypes.create_string_buffer(ctypes.sizeof(SYMBOL_INFO))
        sym = ctypes.cast(buf, ctypes.POINTER(SYMBOL_INFO)).contents
        sym.SizeOfStruct = ctypes.sizeof(SYMBOL_INFO) - MAX_SYM_NAME
        sym.MaxNameLen = MAX_SYM_NAME
        displacement = ctypes.c_ulonglong(0)
        if dbghelp.SymFromAddr(h_process, address, ctypes.byref(displacement), ctypes.byref(sym)):
            print(f"0x{offset:x} -> {sym.Name.decode('utf-8', 'replace')} + 0x{displacement.value:x}")
        else:
            err = ctypes.get_last_error()
            print(f"0x{offset:x} -> SymFromAddr failed, GetLastError=0x{err:x}")

    dbghelp.SymCleanup(h_process)


if __name__ == "__main__":
    main()
