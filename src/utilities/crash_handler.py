"""In-process native-crash capture for Windows, no debugger/registry required.

Installs a SetUnhandledExceptionFilter callback that runs inside the faulting
process at the moment of an unhandled structured exception (e.g. an access
violation from libmpv/FFmpeg/a GPU driver reached through ctypes). Appends a
short text summary (exception code + faulting module!+offset, resolved by
walking loaded modules) into the same faults.log Python's own faulthandler
writes to, so there's one place to look for any crash. Touches no
system/registry state.

Only load-bearing on win32. No-op import elsewhere.
"""
import ctypes
import os
import sys
import time
from ctypes import wintypes

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    # ctypes.windll.X (no declared argtypes/restype) silently mis-marshals
    # some of the psapi calls below -- EnumProcessModules always came back
    # empty despite succeeding. WinDLL(..., use_last_error=True) + explicit
    # argtypes is what actually works.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)

    psapi.EnumProcessModules.restype = wintypes.BOOL
    psapi.EnumProcessModules.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)
    ]
    psapi.GetModuleFileNameExW.restype = wintypes.DWORD
    psapi.GetModuleFileNameExW.argtypes = [
        wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD
    ]
    psapi.GetModuleInformation.restype = wintypes.BOOL
    # argtypes for GetModuleInformation set after MODULEINFO is defined below.

    class EXCEPTION_RECORD(ctypes.Structure):
        pass

    EXCEPTION_RECORD._fields_ = [
        ("ExceptionCode", wintypes.DWORD),
        ("ExceptionFlags", wintypes.DWORD),
        ("ExceptionRecord", ctypes.POINTER(EXCEPTION_RECORD)),
        ("ExceptionAddress", ctypes.c_void_p),
        ("NumberParameters", wintypes.DWORD),
        ("ExceptionInformation", ctypes.c_void_p * 15),
    ]

    class EXCEPTION_POINTERS(ctypes.Structure):
        _fields_ = [
            ("ExceptionRecord", ctypes.POINTER(EXCEPTION_RECORD)),
            ("ContextRecord", ctypes.c_void_p),
        ]

    class MODULEINFO(ctypes.Structure):
        _fields_ = [
            ("lpBaseOfDll", ctypes.c_void_p),
            ("SizeOfImage", wintypes.DWORD),
            ("EntryPoint", ctypes.c_void_p),
        ]

    psapi.GetModuleInformation.argtypes = [
        wintypes.HANDLE, wintypes.HMODULE, ctypes.POINTER(MODULEINFO), wintypes.DWORD
    ]

    LPTOP_LEVEL_EXCEPTION_FILTER = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)

    def _enum_modules_with_ranges():
        h_process = kernel32.GetCurrentProcess()
        needed = wintypes.DWORD(0)
        buf_count = 1024
        while True:
            arr = (wintypes.HMODULE * buf_count)()
            size = ctypes.sizeof(arr)
            if not psapi.EnumProcessModules(h_process, arr, size, ctypes.byref(needed)):
                return []
            if needed.value <= size:
                break
            buf_count = needed.value // ctypes.sizeof(wintypes.HMODULE) + 16

        count = needed.value // ctypes.sizeof(wintypes.HMODULE)
        modules = []
        for i in range(count):
            h_mod = arr[i]
            if not h_mod:
                continue
            name_buf = ctypes.create_unicode_buffer(260)
            psapi.GetModuleFileNameExW(h_process, h_mod, name_buf, 260)
            info = MODULEINFO()
            if psapi.GetModuleInformation(h_process, h_mod, ctypes.byref(info), ctypes.sizeof(info)):
                base = ctypes.cast(info.lpBaseOfDll, ctypes.c_void_p).value or 0
                modules.append((name_buf.value, base, info.SizeOfImage))
        return modules

    def _describe_address(address: int) -> str:
        for name, base, size in _enum_modules_with_ranges():
            if base and base <= address < base + size:
                return f"{os.path.basename(name)}+0x{address - base:x}"
        return f"0x{address:x} (unknown module)"

    def _write_summary(exc_record, fault_log_path: str):
        # Appended into the same faults.log Python's own faulthandler writes
        # to (see log_handler/manager.py) -- one place to look for any crash,
        # native or Python-level, instead of a separate crashes/ folder.
        try:
            code = exc_record.ExceptionCode
            address = exc_record.ExceptionAddress or 0
            address = ctypes.cast(address, ctypes.c_void_p).value or 0
            location = _describe_address(address)
            with open(fault_log_path, "a", encoding="utf-8", errors="replace") as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Native crash (crash_handler) - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*50}\n")
                f.write(f"pid={os.getpid()}\n")
                f.write(f"exception_code=0x{code:08x}\n")
                f.write(f"faulting_address={location}\n")
                if code == 0xC0000005 and exc_record.NumberParameters >= 2:
                    access_type = exc_record.ExceptionInformation[0]
                    fault_addr = exc_record.ExceptionInformation[1]
                    kind = "write" if access_type else "read"
                    f.write(f"access_violation={kind} at 0x{fault_addr:x}\n")
        except Exception:
            pass

    def install_crash_handler(logs_dir: str):
        os.makedirs(logs_dir, exist_ok=True)
        fault_log_path = os.path.join(logs_dir, "faults.log")

        @LPTOP_LEVEL_EXCEPTION_FILTER
        def handler(exception_pointers):
            try:
                ptrs = ctypes.cast(exception_pointers, ctypes.POINTER(EXCEPTION_POINTERS)).contents
                exc_record = ptrs.ExceptionRecord.contents
                _write_summary(exc_record, fault_log_path)
                # A MiniDumpWriteDump attempt used to live here (self-process
                # dump from inside the faulting thread). It never produced a
                # usable dump in practice -- a known-fragile case -- so it's
                # dropped rather than leaving empty .dmp files around. The
                # text summary above plus Windows' own Event Log entry (no
                # setup required: Get-WinEvent -FilterHashtable
                # @{LogName='Application'; Id=1000}) are the reliable sources;
                # scripts/resolve_crash_symbols.py resolves offsets from
                # either against Microsoft's public symbol server.
            except Exception:
                pass
            return 1  # EXCEPTION_EXECUTE_HANDLER: let the process die after we've logged

        # keep a reference alive for the life of the process, otherwise the
        # ctypes callback trampoline gets garbage collected
        install_crash_handler._handler_ref = handler
        kernel32.SetUnhandledExceptionFilter(handler)

else:
    def install_crash_handler(logs_dir: str):
        pass
