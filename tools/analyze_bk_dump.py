from __future__ import annotations

import argparse
import collections
import hashlib
import math
import re
from pathlib import Path


ASCII_RE = re.compile(rb"[\x20-\x7e]{4,}")
UTF16LE_RE = re.compile(rb"(?:[\x20-\x7e]\x00){4,}")
INTEREST_RE = re.compile(
    rb"tuya|bk7231|cb3s|product|schema|firmware|version|uart|baud|serial|garage|door|"
    rb"wifi|mqtt|json|uuid|auth|key|pid|dpid|dps|mcu|ota|rbl|user_param|gw_",
    re.IGNORECASE,
)


def entropy(block: bytes) -> float:
    if not block:
        return 0.0
    counts = collections.Counter(block)
    size = len(block)
    return -sum((n / size) * math.log2(n / size) for n in counts.values())


def escaped(raw: bytes, limit: int = 240) -> str:
    raw = raw[:limit]
    return raw.decode("ascii", "backslashreplace")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dump", type=Path)
    parser.add_argument("--brief", action="store_true")
    args = parser.parse_args()
    data = args.dump.read_bytes()

    print(f"size={len(data)} (0x{len(data):X})")
    print(f"sha256={hashlib.sha256(data).hexdigest()}")
    print(f"first32={data[:32].hex(' ')}")
    print(f"last32={data[-32:].hex(' ')}")

    print("\n4 KiB block summary (non-FF/non-00 ranges and entropy transitions):")
    block_size = 0x1000
    rows: list[tuple[int, int, int, float]] = []
    for offset in range(0, len(data), block_size):
        block = data[offset : offset + block_size]
        rows.append((offset, block.count(0xFF), block.count(0x00), entropy(block)))

    # Collapse consecutive blocks with similar high-level character.
    def kind(row: tuple[int, int, int, float]) -> str:
        _, ff, zero, ent = row
        if ff == block_size:
            return "all-FF"
        if zero == block_size:
            return "all-00"
        if ent > 7.5:
            return "high-entropy"
        if ent > 5.0:
            return "mixed"
        return "low-entropy"

    start = 0
    current = kind(rows[0])
    for i in range(1, len(rows) + 1):
        next_kind = kind(rows[i]) if i < len(rows) else None
        if next_kind != current:
            segment = rows[start:i]
            entropies = [r[3] for r in segment]
            print(
                f"  0x{segment[0][0]:06X}-0x{segment[-1][0] + block_size - 1:06X} "
                f"{current:12s} blocks={len(segment):3d} "
                f"entropy={min(entropies):.2f}..{max(entropies):.2f}"
            )
            start = i
            current = next_kind

    strings = [(m.start(), m.group()) for m in ASCII_RE.finditer(data)]
    wide_strings = [(m.start(), m.group()[::2]) for m in UTF16LE_RE.finditer(data)]
    print(f"\nascii_strings={len(strings)} utf16le_strings={len(wide_strings)}")

    print("\nInteresting strings:")
    hits = [(off, raw) for off, raw in strings + wide_strings if INTEREST_RE.search(raw)]
    for off, raw in sorted(hits)[:500]:
        print(f"  0x{off:06X}  {escaped(raw)}")
    if len(hits) > 500:
        print(f"  ... {len(hits) - 500} more")

    if not args.brief:
        print("\nLong strings (>=32 bytes):")
        for off, raw in strings:
            if len(raw) >= 32:
                print(f"  0x{off:06X} len={len(raw):4d}  {escaped(raw)}")

    print("\nCandidate JSON fragments:")
    json_rows = []
    for off, raw in strings:
        if b"{" in raw or b"}" in raw or b"\":\"" in raw or b"\"dp" in raw.lower():
            json_rows.append((off, raw))
    seen_json: set[bytes] = set()
    for off, raw in json_rows:
        if args.brief and raw in seen_json:
            continue
        seen_json.add(raw)
        print(f"  0x{off:06X}  {escaped(raw)}")
        if args.brief and len(seen_json) >= 100:
            print(f"  ... limited to {len(seen_json)} unique fragments")
            break


if __name__ == "__main__":
    main()
