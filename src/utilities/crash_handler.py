"""In-process native-crash capture for Windows, no debugger/registry required.

Installs a SetUnhandledExceptionFilter callback that runs inside the faulting
process at the moment of an unhandled structured exception (e.g. an access
violation from libmpv/FFmpeg/a GPU driver reached through ctypes). It writes a
minidump via dbghelp!MiniDumpWriteDump and a short text summary (exception
code + faulting module!+offset, resolved by walking loaded modules) before the
process terminates. This is the same mechanism crash reporters like
Sentry/Backtrace use; it touches no system/registry state.

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
    dbghelp = ctypes.WinDLL("dbghelp", use_last_error=True)
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

    class MINIDUMP_EXCEPTION_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("ThreadId", wintypes.DWORD),
            ("ExceptionPointers", ctypes.c_void_p),
            ("ClientPointers", wintypes.BOOL),
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

    MiniDumpNormal = 0x00000000
    MiniDumpWithDataSegs = 0x00000001
    GENERIC_WRITE = 0x40000000
    CREATE_ALWAYS = 2
    FILE_ATTRIBUTE_NORMAL = 0x80

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

    def _write_summary(exc_record, summary_path: str):
        try:
            code = exc_record.ExceptionCode
            address = exc_record.ExceptionAddress or 0
            address = ctypes.cast(address, ctypes.c_void_p).value or 0
            location = _describe_address(address)
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(f"pid={os.getpid()}\n")
                f.write(f"time={time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"exception_code=0x{code:08x}\n")
                f.write(f"faulting_address={location}\n")
                if code == 0xC0000005 and exc_record.NumberParameters >= 2:
                    access_type = exc_record.ExceptionInformation[0]
                    fault_addr = exc_record.ExceptionInformation[1]
                    kind = "write" if access_type else "read"
                    f.write(f"access_violation={kind} at 0x{fault_addr:x}\n")
        except Exception as e:
            try:
                with open(summary_path, "a", encoding="utf-8") as f:
                    f.write(f"(failed to fully decode exception: {e})\n")
            except Exception:
                pass

    def install_crash_handler(dump_dir: str):
        os.makedirs(dump_dir, exist_ok=True)

        @LPTOP_LEVEL_EXCEPTION_FILTER
        def handler(exception_pointers):
            try:
                stamp = f"{int(time.time())}_{os.getpid()}"
                dump_path = os.path.join(dump_dir, f"crash_{stamp}.dmp")
                summary_path = os.path.join(dump_dir, f"crash_{stamp}.txt")

                ptrs = ctypes.cast(exception_pointers, ctypes.POINTER(EXCEPTION_POINTERS)).contents
                exc_record = ptrs.ExceptionRecord.contents
                _write_summary(exc_record, summary_path)

                h_process = kernel32.GetCurrentProcess()
                pid = kernel32.GetCurrentProcessId()
                h_file = kernel32.CreateFileW(dump_path, GENERIC_WRITE, 0, None, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, None)
                if h_file and h_file != -1:
                    exc_info = MINIDUMP_EXCEPTION_INFORMATION(
                        ThreadId=kernel32.GetCurrentThreadId(),
                        ExceptionPointers=exception_pointers,
                        ClientPointers=False,
                    )
                    ok = dbghelp.MiniDumpWriteDump(
                        h_process, pid, h_file,
                        MiniDumpNormal | MiniDumpWithDataSegs,
                        ctypes.byref(exc_info), None, None,
                    )
                    if not ok:
                        err = kernel32.GetLastError()
                        with open(summary_path, "a", encoding="utf-8") as f:
                            f.write(f"MiniDumpWriteDump failed, GetLastError=0x{err:x}\n")
                    kernel32.CloseHandle(h_file)
            except Exception:
                pass
            return 1  # EXCEPTION_EXECUTE_HANDLER: let the process die after we've dumped

        # keep a reference alive for the life of the process, otherwise the
        # ctypes callback trampoline gets garbage collected
        install_crash_handler._handler_ref = handler
        kernel32.SetUnhandledExceptionFilter(handler)

else:
    def install_crash_handler(dump_dir: str):
        pass
