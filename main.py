#!/usr/bin/env python3
"""THE GLOBAL DISPATCH, LATE EDITION — 26 November 2026 in one image.

Entrypoint for the make.fun news-image-20261126 bounty (v2 test entry,
built with the news-image skill v2.4.0). The program ships the finished
broadsheet — entry.png, rendered from hand-written HTML/CSS as text,
no image generator — and places it in the grader's output directory.

The image sums up Thursday, 26 November 2026 in 36 unique stories,
each first reported that day: a lead on Kim Jong Un's tactical-nuke
order, four drawn pictograms, a world map with six story pins, a UTC
timeline, a key-figures panel, and four regional columns. Two stories
were refreshed for the late edition ([19] Israel kills nine in Gaza
overnight, [35] Congo Ebola cases pass 12,000). A full source ledger
(traceability-ledger.json) records where every story came from.

Nothing is fetched at run time and the output is byte-identical on
every run: it is a straight copy of the file bundled in this repo.
"""

import hashlib
import os
import struct
import sys

# The bundled image sits next to this file.
HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLED = os.path.join(HERE, "entry.png")

# The grader's output directory; /output unless overridden.
OUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
OUT_PATH = os.path.join(OUT_DIR, "entry.png")

# Kit limits for this bounty: 1 MiB, at most 1024 px per side.
BYTE_CAP = 1_048_576
SIDE_CAP = 1024

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def digest_bytes(data):
    """SHA-256 hex digest of a bytes object."""
    return hashlib.sha256(data).hexdigest()


def png_dimensions(data):
    """Walk the PNG chunk list; return (width, height) from IHDR.

    Also confirms the file ends with a proper IEND chunk, so a
    truncated file is caught instead of shipped.
    """
    if data[:8] != PNG_SIGNATURE:
        raise ValueError("entry.png is not a PNG file")
    offset = 8
    width = height = None
    saw_iend = False
    while offset + 8 <= len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        if chunk_type == b"IHDR":
            width, height = struct.unpack(">II", data[offset + 8:offset + 16])
        if chunk_type == b"IEND":
            saw_iend = True
            break
        offset += 12 + length
    if width is None:
        raise ValueError("entry.png has no IHDR chunk")
    if not saw_iend:
        raise ValueError("entry.png is truncated: no IEND chunk")
    return width, height


def validate(data):
    """Enforce the kit's byte and dimension limits; return dimensions."""
    if len(data) > BYTE_CAP:
        raise ValueError(f"entry.png is {len(data)} bytes, over the 1 MiB cap")
    width, height = png_dimensions(data)
    if width > SIDE_CAP or height > SIDE_CAP:
        raise ValueError(
            f"entry.png is {width}x{height}, over the 1024x1024 cap"
        )
    return width, height


def main():
    with open(BUNDLED, "rb") as handle:
        data = handle.read()
    width, height = validate(data)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PATH, "wb") as handle:
        handle.write(data)
    # Re-read what was written and confirm it matches the bundle.
    with open(OUT_PATH, "rb") as handle:
        written = handle.read()
    if digest_bytes(written) != digest_bytes(data):
        raise ValueError("written entry.png does not match the bundle")
    print(
        f"wrote {OUT_PATH}: {width}x{height}, {len(data)} bytes, "
        f"sha256 {digest_bytes(data)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
