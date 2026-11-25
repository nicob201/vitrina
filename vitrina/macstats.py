"""What the Mac panel reads from macOS: straight from the system (Mach, IOKit, getifaddrs), so the reading
every few seconds starts no program. Only pmset (every half hour) and scutil (once) are run as commands.
Nothing is loaded on import: the system libraries open on first use, so importing this anywhere is harmless."""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
from ctypes import POINTER, Structure, byref, c_char_p, c_int, c_int64, c_uint, c_uint8, c_uint32, c_uint64, c_void_p
from functools import lru_cache

from .metrics import memory_used, parse_battery

_HOST_CPU_LOAD_INFO = 3
_HOST_VM_INFO64 = 4
_AF_LINK = 18
_IF_BYTES = 40           # offset of ifi_ibytes, followed by ifi_obytes, in struct if_data
_CF_UTF8 = 0x08000100    # kCFStringEncodingUTF8
_CF_SINT64 = 4           # kCFNumberSInt64Type


class _VmStats(Structure):  # struct vm_statistics64, <mach/vm_statistics.h>
    _fields_ = [
        ("free", c_uint32), ("active", c_uint32), ("inactive", c_uint32), ("wire", c_uint32),
        ("zero_fill", c_uint64), ("reactivations", c_uint64), ("pageins", c_uint64), ("pageouts", c_uint64),
        ("faults", c_uint64), ("cow_faults", c_uint64), ("lookups", c_uint64), ("hits", c_uint64),
        ("purges", c_uint64), ("purgeable", c_uint32), ("speculative", c_uint32),
        ("decompressions", c_uint64), ("compressions", c_uint64), ("swapins", c_uint64), ("swapouts", c_uint64),
        ("compressor", c_uint32), ("throttled", c_uint32), ("external", c_uint32), ("internal", c_uint32),
        ("total_uncompressed", c_uint64),
    ]


class _SockAddr(Structure):
    _fields_ = [("len", c_uint8), ("family", c_uint8)]


class _IfAddrs(Structure):  # struct ifaddrs, <ifaddrs.h>
    pass


_IfAddrs._fields_ = [("next", POINTER(_IfAddrs)), ("name", c_char_p), ("flags", c_uint), ("addr", POINTER(_SockAddr)),
                     ("netmask", c_void_p), ("dstaddr", c_void_p), ("data", c_void_p)]


@lru_cache(maxsize=None)
def _libc():
    lib = ctypes.CDLL("/usr/lib/libSystem.dylib")
    lib.mach_host_self.restype = c_uint
    lib.mach_host_self.argtypes = []
    lib.host_statistics.argtypes = [c_uint, c_int, c_void_p, POINTER(c_uint)]
    lib.host_statistics64.argtypes = [c_uint, c_int, c_void_p, POINTER(c_uint)]
    lib.getifaddrs.argtypes = [POINTER(POINTER(_IfAddrs))]
    lib.freeifaddrs.argtypes = [POINTER(_IfAddrs)]
    return lib


@lru_cache(maxsize=None)
def _host() -> int:
    # Asked once: every mach_host_self() call adds a reference to the port that is never given back.
    return _libc().mach_host_self()


@lru_cache(maxsize=None)
def _iokit():
    iokit = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
    cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    iokit.IOServiceMatching.restype = c_void_p
    iokit.IOServiceMatching.argtypes = [c_char_p]
    iokit.IOServiceGetMatchingServices.argtypes = [c_uint, c_void_p, POINTER(c_uint)]
    iokit.IOIteratorNext.restype = c_uint
    iokit.IOIteratorNext.argtypes = [c_uint]
    iokit.IORegistryEntryCreateCFProperty.restype = c_void_p
    iokit.IORegistryEntryCreateCFProperty.argtypes = [c_uint, c_void_p, c_void_p, c_uint]
    iokit.IOObjectRelease.argtypes = [c_uint]
    cf.CFStringCreateWithCString.restype = c_void_p
    cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_uint]
    cf.CFDictionaryGetValue.restype = c_void_p
    cf.CFDictionaryGetValue.argtypes = [c_void_p, c_void_p]
    cf.CFNumberGetValue.restype = ctypes.c_bool
    cf.CFNumberGetValue.argtypes = [c_void_p, c_int, c_void_p]
    cf.CFRelease.argtypes = [c_void_p]
    # Kept for the life of the process: two keys, created once.
    keys = (cf.CFStringCreateWithCString(None, b"PerformanceStatistics", _CF_UTF8),
            cf.CFStringCreateWithCString(None, b"Device Utilization %", _CF_UTF8))
    return iokit, cf, keys


def read_cpu_ticks() -> tuple[int, int, int, int]:
    """Ticks since boot spent in (user, system, idle, nice), all cores together."""
    info, count = (c_uint * 4)(), c_uint(4)
    kr = _libc().host_statistics(_host(), _HOST_CPU_LOAD_INFO, info, byref(count))
    if kr != 0:
        raise OSError(f"host_statistics failed ({kr})")
    return info[0], info[1], info[2], info[3]


def read_memory_used() -> int:
    stats = _VmStats()
    count = c_uint(ctypes.sizeof(_VmStats) // 4)
    kr = _libc().host_statistics64(_host(), _HOST_VM_INFO64, byref(stats), byref(count))
    if kr != 0:
        raise OSError(f"host_statistics64 failed ({kr})")
    return memory_used(stats.internal, stats.purgeable, stats.wire, stats.compressor, os.sysconf("SC_PAGESIZE"))


def read_gpu() -> float | None:
    """The busiest GPU's utilization, as Activity Monitor shows it; None if no GPU reports one."""
    iokit, cf, (perf_key, util_key) = _iokit()
    found = c_uint()
    # IOServiceGetMatchingServices takes over (and releases) the matching dictionary.
    kr = iokit.IOServiceGetMatchingServices(0, iokit.IOServiceMatching(b"IOAccelerator"), byref(found))
    if kr != 0:
        raise OSError(f"IOServiceGetMatchingServices failed ({kr})")
    best = None
    try:
        while True:
            service = iokit.IOIteratorNext(found.value)
            if not service:
                break
            try:
                stats = iokit.IORegistryEntryCreateCFProperty(service, perf_key, None, 0)
                if not stats:
                    continue
                try:
                    value = cf.CFDictionaryGetValue(stats, util_key)
                    number = c_int64()
                    if value and cf.CFNumberGetValue(value, _CF_SINT64, byref(number)):
                        best = float(number.value) if best is None else max(best, float(number.value))
                finally:
                    cf.CFRelease(stats)
            finally:
                iokit.IOObjectRelease(service)
    finally:
        iokit.IOObjectRelease(found.value)
    return best


def read_net() -> tuple[int, int]:
    """Bytes received and sent since boot (32-bit counters) on Wi-Fi and Ethernet. Only en* interfaces:
    a VPN's traffic also crosses en0, and counting its tunnel too would count it twice."""
    lib = _libc()
    head = POINTER(_IfAddrs)()
    if lib.getifaddrs(byref(head)) != 0:
        raise OSError("getifaddrs failed")
    received = sent = 0
    try:
        entry = head
        while entry:
            item = entry.contents
            if (item.addr and item.addr.contents.family == _AF_LINK and item.data
                    and item.name and item.name.startswith(b"en")):
                counters = (c_uint32 * 2).from_address(item.data + _IF_BYTES)
                received += counters[0]
                sent += counters[1]
            entry = item.next
    finally:
        lib.freeifaddrs(head)
    return received, sent


def ram_total() -> int:
    return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGESIZE")


def read_disk() -> dict:
    usage = shutil.disk_usage("/")
    return {"free": usage.free, "total": usage.total}


def read_battery(run=subprocess.run) -> dict | None:
    out = run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=10)
    return parse_battery(out.stdout) if out.returncode == 0 else None


def computer_name(run=subprocess.run) -> str:
    """The name in System Settings > General > Sharing; "Mac" if it can't be read."""
    try:
        out = run(["scutil", "--get", "ComputerName"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "Mac"
    name = out.stdout.strip() if out.returncode == 0 else ""
    return name or "Mac"


READERS = {"cpu": read_cpu_ticks, "ram": read_memory_used, "gpu": read_gpu, "net": read_net}
SLOW_READERS = {"disk": read_disk, "battery": read_battery}
