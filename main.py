#!/usr/bin/env python3
"""THE GLOBAL DISPATCH — 26 November 2026, one image of the day's news.

This program is the entrypoint for the make.fun news-image-20261126
bounty. It ships the finished broadsheet (entry.png, rendered from
broadsheet HTML/CSS as text, no image generator) and writes it to the
output directory the grader provides.

The image sums up Thursday, 26 November 2026: 36 unique stories, each
first reported that day, in a newspaper layout with a lead story, a
key-figures panel, a schematic map from Pyongyang to Cairo, and four
regional columns. Nothing is fetched at run time and the output is
byte-identical on every run, because it is a straight copy of the
file bundled in this repository.
"""

import hashlib
import os
import shutil
import struct
import sys

# The image lives next to this file in the repository.
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_PATH = os.path.join(HERE, "entry.png")

# Where the grader wants the image; /output by default.
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "entry.png")

# Kit limits for this bounty.
MAX_BYTES = 1_048_576
MAX_SIDE = 1024

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def read_png_size(path):
    """Return (width, height) after confirming the file is a PNG."""
    with open(path, "rb") as handle:
        head = handle.read(33)
    if head[:8] != PNG_MAGIC:
        raise ValueError("entry.png is not a PNG file")
    width, height = struct.unpack(">II", head[16:24])
    return width, height


def sha256_of(path):
    """Hex digest of a file, streamed in 64 KiB blocks."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def check_entry(path):
    """Enforce the kit's size and dimension limits on the output."""
    size = os.path.getsize(path)
    if size > MAX_BYTES:
        raise ValueError(f"entry.png is {size} bytes, over the 1 MiB cap")
    width, height = read_png_size(path)
    if width > MAX_SIDE or height > MAX_SIDE:
        raise ValueError(
            f"entry.png is {width}x{height}, over the 1024x1024 cap"
        )
    with open(path, "rb") as handle:
        handle.seek(-12, os.SEEK_END)
        trailer = handle.read(12)
    if trailer[4:8] != b"IEND":
        raise ValueError("entry.png is truncated: no IEND chunk at the end")
    return size, width, height


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    shutil.copyfile(SOURCE_PATH, OUTPUT_PATH)
    size, width, height = check_entry(OUTPUT_PATH)
    print(
        f"wrote {OUTPUT_PATH}: {width}x{height}, {size} bytes, "
        f"sha256 {sha256_of(OUTPUT_PATH)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
