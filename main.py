#!/usr/bin/env python3
"""THE WORLD IN ONE DAY — Thursday 26 November 2026 in one image.

Entrypoint for the make.fun news-image-20261126 bounty, v3 rebuild
(built with the news-image skill v2.4.4, winner-template layout §6.7).

The program ships the finished broadsheet — entry.png, rendered from
hand-written HTML/CSS as text, no image generator — and places it in
the grader's output directory. One page, no gaps: 13 illustrated
scenes (3 large leads + 10 smaller scenes, each drawn fresh for its
story), a pin-matched world map drawn fresh for this edition, a dense
numbered briefs list for stories 14–36, a UTC timeline, a key-figures
strip, a region bar, a date-check list of excluded stories, and a
HOW SURE legend. All 36 stories happened or were first reported on
Thursday 26 November 2026; the source ledger (traceability-ledger.json)
records where every story came from.

Nothing is fetched at run time and the output is byte-identical on
every run: it is a straight copy of the file bundled in this repo,
written directly to the output path (no temporary file in the output
folder, which the grader forbids).
"""

import argparse
import hashlib
import os
import struct
import sys
import tempfile
from collections import namedtuple

# The bundled image sits next to this file.
HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLED = os.path.join(HERE, "entry.png")

# Kit limits for this bounty: 1 MiB, at most 1024 px per side.
MAX_BYTES = 1_048_576
MAX_SIDE = 1024
VERSION = "3.0.0"

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# One PNG chunk: its four-letter type and its payload bytes.
Chunk = namedtuple("Chunk", ["kind", "payload"])


def iter_chunks(data):
    """Yield every chunk of a PNG, in file order.

    Each chunk is length (4 bytes, big-endian), type (4 bytes),
    payload, and CRC (4 bytes). A chunk whose declared length runs
    past the end of the file stops the walk with an error instead of
    silently truncating the image.
    """
    if data[:8] != PNG_SIGNATURE:
        raise ValueError("entry.png is not a PNG file")
    offset = 8
    while offset + 8 <= len(data):
        (length,) = struct.unpack(">I", data[offset:offset + 4])
        kind = data[offset + 4:offset + 8]
        start = offset + 8
        end = start + length
        if end + 4 > len(data):
            raise ValueError("truncated PNG chunk %r" % kind)
        yield Chunk(kind, data[start:end])
        offset = end + 4
    if offset != len(data):
        raise ValueError("trailing bytes after the last PNG chunk")


class PngReport(object):
    """What the inspection of the bundled image found."""

    def __init__(self, data):
        self.data = data
        self.bytes = len(data)
        self.digest = hashlib.sha256(data).hexdigest()
        self.width = None
        self.height = None
        self.chunks = 0
        self.saw_iend = False
        self._walk()

    def _walk(self):
        for chunk in iter_chunks(self.data):
            self.chunks += 1
            if chunk.kind == b"IHDR":
                if len(chunk.payload) != 13:
                    raise ValueError("IHDR chunk has the wrong size")
                (self.width, self.height) = struct.unpack(
                    ">II", chunk.payload[:8])
            elif chunk.kind == b"IEND":
                self.saw_iend = True
        if self.width is None:
            raise ValueError("no IHDR chunk found")
        if not self.saw_iend:
            raise ValueError("no IEND chunk found: image is truncated")

    def check_limits(self):
        """Enforce the kit's size limits; raise on any breach."""
        problems = []
        if self.bytes > MAX_BYTES:
            problems.append("image is %d bytes, over the %d-byte cap"
                            % (self.bytes, MAX_BYTES))
        if self.width > MAX_SIDE or self.height > MAX_SIDE:
            problems.append("image is %dx%d, over the %dx%d cap"
                            % (self.width, self.height, MAX_SIDE, MAX_SIDE))
        if problems:
            raise ValueError("; ".join(problems))

    def summary(self):
        return ("%dx%d PNG, %d bytes, %d chunks, sha256 %s"
                % (self.width, self.height, self.bytes,
                   self.chunks, self.digest[:16]))


def load_bundled():
    """Read the bundled image and return its inspection report."""
    with open(BUNDLED, "rb") as handle:
        data = handle.read()
    report = PngReport(data)
    report.check_limits()
    return report


def deliver(report, out_path):
    """Write the image to out_path, then verify it.

    The bytes go straight to the output path: the grader requires the
    output folder to hold exactly the one entry file, so no temporary
    file may appear in it. The file is made world-readable (0644) so
    the grader can read it whoever runs the check. After the write
    the file is read back and its digest compared with the bundled
    one; a mismatch is an error, not a silent success. If the write
    fails, a half-written output is removed instead of left behind.
    """
    out_dir = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(out_dir, exist_ok=True)
    try:
        with open(out_path, "wb") as handle:
            handle.write(report.data)
        os.chmod(out_path, 0o644)
    except BaseException:
        try:
            os.unlink(out_path)
        except OSError:
            pass
        raise
    with open(out_path, "rb") as handle:
        written = handle.read()
    if hashlib.sha256(written).hexdigest() != report.digest:
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
        report = load_bundled()
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("bundled: %s" % report.summary())
    if args.check:
        print("check passed: image is valid and within the kit limits")
        return 0
    if args.self_test:
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "entry.png")
            deliver(report, target)
            print("self-test passed: delivered and verified at %s" % target)
        return 0
    out_path = args.out
    if out_path is None:
        out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
        out_path = os.path.join(out_dir, "entry.png")
    try:
        deliver(report, out_path)
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("wrote %s" % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
