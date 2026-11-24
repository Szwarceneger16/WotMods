# -*- coding: utf-8 -*-
"""Order detached results at observation time, before any disk worker runs."""
from __future__ import unicode_literals

import hashlib
import os
import time
import uuid

from .normalize import text_type

integer_types = (int, type(2 ** 64))


def _windows_boot_domain(ctypes):
    # SystemBootEnvironmentInformation starts with a 16-byte BootIdentifier.
    # This read-only native query is optional on future Windows versions. Use
    # one source for all clients so a missing registry value cannot give peers
    # on the same boot two different identities.
    query = ctypes.windll.ntdll.NtQuerySystemInformation
    query.argtypes = [ctypes.c_uint, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
    query.restype = ctypes.c_long
    info, length = ctypes.create_string_buffer(64), ctypes.c_ulong()
    status = query(0x5a, info, ctypes.sizeof(info), ctypes.byref(length))
    if status != 0 or not 16 <= length.value <= ctypes.sizeof(info):
        return None
    identifier = info.raw[:16]
    if identifier == b'\x00' * 16:
        return None
    return text_type(hashlib.sha256(b'windows-qpc\x00' + identifier).hexdigest()[:32])


def _boot_clock():
    try:
        if os.name == 'nt':
            import ctypes
            domain = _windows_boot_domain(ctypes)
            if domain is None:
                return None, None
            counter = ctypes.windll.kernel32.QueryPerformanceCounter
            counter.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
            counter.restype = ctypes.c_int

            def tick():
                value = ctypes.c_longlong()
                return value.value if counter(ctypes.byref(value)) else 0

            return domain, tick
        with open('/proc/sys/kernel/random/boot_id', 'rb') as handle:
            domain = text_type(uuid.UUID(handle.read(40).decode('ascii').strip()).hex)
        monotonic = getattr(time, 'monotonic', None)
        if monotonic is not None:
            return domain, lambda: int(monotonic() * 1000000000)
        # Linux integration runs the same storage path on CPython 2.7.
        import ctypes

        class Timespec(ctypes.Structure):
            _fields_ = [('seconds', ctypes.c_long), ('nanoseconds', ctypes.c_long)]

        counter = ctypes.CDLL(None).clock_gettime
        counter.argtypes = [ctypes.c_int, ctypes.POINTER(Timespec)]
        counter.restype = ctypes.c_int

        def tick():
            value = Timespec()
            return value.seconds * 1000000000 + value.nanoseconds if counter(1, ctypes.byref(value)) == 0 else 0

        return domain, tick
    except (AttributeError, ImportError, IOError, OSError, TypeError, ValueError):
        return None, None


class CaptureClock(object):
    def __init__(self):
        self.domain, self._tick = _boot_clock()
        self._producer = text_type(uuid.uuid4().hex)
        self._sequence = 0
        self._last_wall = 0

    def stamp(self):
        self._sequence += 1
        wall = max(self._last_wall, int(time.time() * 1000000))
        self._last_wall = wall
        ticks = self._tick() if self._tick is not None else 0
        return [wall, self.domain if ticks > 0 else None, max(0, ticks), self._producer, self._sequence]


def _valid_id(value):
    return (isinstance(value, text_type) and len(value) == 32 and
            all(char in '0123456789abcdef' for char in value))


def valid_capture_order(value):
    return (isinstance(value, list) and len(value) == 5 and
            all(type(value[index]) in integer_types and 0 <= value[index] < 2 ** 64 for index in (0, 2, 4)) and
            (value[1] is None or _valid_id(value[1])) and _valid_id(value[3]))


def compare_capture_order(incoming, stored, active_domain):
    """Return a chronological comparison, or None for unrelated clocks."""
    if incoming[3] == stored[3]:
        first, second = incoming[4], stored[4]
    elif incoming[1] is not None and incoming[1] == stored[1]:
        first, second = incoming[2], stored[2]
    elif active_domain is not None and incoming[1] is not None and stored[1] is not None:
        if incoming[1] == active_domain or stored[1] == active_domain:
            # A current boot starts after committed history from older boots.
            return 1 if incoming[1] == active_domain else -1
        return None
    else:
        # The wall clock can move in either direction independently of result
        # delivery. It is diagnostic information only, never merge authority.
        return None
    return (first > second) - (first < second)
