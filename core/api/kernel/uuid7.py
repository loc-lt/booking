import os
import time
import uuid

_RAND_B_MASK = (1 << 62) - 1


def uuid7() -> uuid.UUID:
    """RFC 9562 UUID version 7: 48-bit Unix milliseconds, then random bits.

    Keys sort by creation time, so B-tree inserts land at the right edge of the index.
    Replace with uuid.uuid7() once the project runs on Python 3.14.
    """
    unix_ms = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10))
    rand_a = (rand >> 68) & 0xFFF
    rand_b = rand & _RAND_B_MASK
    value = (unix_ms & 0xFFFF_FFFF_FFFF) << 80 | 0x7 << 76 | rand_a << 64 | 0b10 << 62 | rand_b
    return uuid.UUID(int=value)
