#!/usr/bin/env python3
"""THE WORLD IN ONE DAY — Thursday 26 November 2026 in one image.

Entrypoint for the make.fun news-image-20261126 bounty, v4 rebuild
(a from-scratch rebuild of the v3 broadsheet: 13 scenes redrawn, a
more detailed pin-matched world map, cleaner headline-only briefs).

The program ships the finished broadsheet — entry.png, rendered from
hand-written HTML/CSS as text, no image generator — and places it in
the grader's output directory. One page, no gaps: 13 illustrated
scenes (3 large leads + 10 smaller scenes, each drawn fresh for its
story), a pin-matched world map drawn fresh for this edition, a dense
numbered briefs list for stories 14-36, a UTC timeline, a key-figures
strip, a region bar, a date-check list of excluded stories, and a
HOW SURE legend. All 36 stories happened or were first reported on
Thursday 26 November 2026; the source ledger (traceability-ledger.json)
records where every story came from.

Nothing is fetched at run time and the output is byte-identical on
every run: it is a straight copy of the file bundled in this repo,
delivered through a temporary file and an atomic rename so the grader
never sees a half-written image.
"""

import argparse
import binascii
import hashlib
import os
import struct
import sys
import tempfile

# The bundled image sits next to this file.
HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLED = os.path.join(HERE, "entry.png")

# Kit limits for this bounty: 1 MiB, at most 1024 px per side.
LIMIT_BYTES = 1_048_576
LIMIT_SIDE = 1024
VERSION = "4.0.0"

MAGIC = b"\x89PNG\r\n\x1a\n"


class EntryImage:
    """A parsed copy of the bundled image, with its vital statistics."""

    def __init__(self, data):
        self.data = data
        self.nbytes = len(data)
        self.digest = hashlib.sha256(data).hexdigest()
        self.width = 0
        self.height = 0
        self.nchunks = 0
        self.has_iend = False
        self._parse()

    def _parse(self):
        if self.data[:8] != MAGIC:
            raise ValueError("entry.png is not a PNG file")
        pos = 8
        while pos + 8 <= len(self.data):
            (size,) = struct.unpack(">I", self.data[pos:pos + 4])
            kind = self.data[pos + 4:pos + 8]
            body = self.data[pos + 8:pos + 8 + size]
            if len(body) != size or pos + 12 + size > len(self.data):
                raise ValueError("truncated PNG chunk %r" % kind)
            (stored_crc,) = struct.unpack(
                ">I", self.data[pos + 8 + size:pos + 12 + size])
            actual_crc = binascii.crc32(kind + body) & 0xFFFFFFFF
            if stored_crc != actual_crc:
                raise ValueError("bad CRC in PNG chunk %r" % kind)
            self.nchunks += 1
            if kind == b"IHDR":
                if len(body) != 13:
                    raise ValueError("IHDR chunk has the wrong size")
                (self.width, self.height) = struct.unpack(">II", body[:8])
            elif kind == b"IEND":
                self.has_iend = True
            pos += 12 + size
        if pos != len(self.data):
            raise ValueError("trailing bytes after the last PNG chunk")
        if not self.width:
            raise ValueError("no IHDR chunk found")
        if not self.has_iend:
            raise ValueError("no IEND chunk found: image is truncated")

    def check_limits(self):
        """Enforce the kit's size limits; raise on any breach."""
        faults = []
        if self.nbytes > LIMIT_BYTES:
            faults.append("image is %d bytes, over the %d-byte cap"
                          % (self.nbytes, LIMIT_BYTES))
        if self.width > LIMIT_SIDE or self.height > LIMIT_SIDE:
            faults.append("image is %dx%d, over the %dx%d cap"
                          % (self.width, self.height, LIMIT_SIDE, LIMIT_SIDE))
        if faults:
            raise ValueError("; ".join(faults))

    def describe(self):
        return ("%dx%d PNG, %d bytes, %d chunks, sha256 %s"
                % (self.width, self.height, self.nbytes,
                   self.nchunks, self.digest[:16]))


def load_image():
    """Read the bundled image and return its parsed form."""
    with open(BUNDLED, "rb") as handle:
        return EntryImage(handle.read())


def ship(image, out_path):
    """Write the image to out_path atomically, then verify it.

    The bytes go to a temporary file in the same directory first and
    are moved into place with os.replace, so a reader never sees a
    partial file. After the move the file is read back and its digest
    compared with the bundled one; a mismatch is an error, not a
    silent success.
    """
    folder = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".entry-", dir=folder)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(image.data)
        os.replace(tmp_path, out_path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    with open(out_path, "rb") as handle:
        written = handle.read()
    if hashlib.sha256(written).hexdigest() != image.digest:
        raise ValueError("written file does not match the bundled image")
    return out_path


def build_parser():
    parser = argparse.ArgumentParser(
        description="Ship the 26 November 2026 broadsheet to the output directory.")
    parser.add_argument(
        "--out", default=None,
        help="destination file (default: $MAKEFUN_OUTPUT_DIR/entry.png, else /output/entry.png)")
    parser.add_argument(
        "--check", action="store_true",
        help="only inspect the bundled image; write nothing")
    parser.add_argument(
        "--self-test", action="store_true",
        help="deliver to a temporary directory and verify, then clean up")
    parser.add_argument(
        "--version", action="version",
        version="%(prog)s " + VERSION)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        image = load_image()
        image.check_limits()
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("bundled: %s" % image.describe())
    if args.check:
        print("check passed: image is valid and within the kit limits")
        return 0
    if args.self_test:
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "entry.png")
            ship(image, target)
            print("self-test passed: delivered and verified at %s" % target)
        return 0
    out_path = args.out
    if out_path is None:
        out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
        out_path = os.path.join(out_dir, "entry.png")
    try:
        ship(image, out_path)
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("wrote %s" % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
