from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

from capstone import CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_LITTLE_ENDIAN, CS_MODE_THUMB, Cs
from capstone.arm import ARM_OP_MEM, ARM_REG_PC


BASE = 0x10000
ASCII_RE = re.compile(rb"[\x20-\x7e]{4,}")
TARGETS = (
    b"tuya_app_main.c",
    b"SOC Rev DP Raw Cmd",
    b"CB3S_Opener",
    b"door_ctrl_comm.c",
    b"open the door!",
    b"stop the door!",
    b"close the door!",
    b"WIFI Module, CB3S",
    b"firmware compiled at",
    b"baud",
)


def render_insn(insn) -> str:
    return f"0x{insn.address:08X}: {insn.mnemonic:8s} {insn.op_str}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    data = args.image.read_bytes()

    print("Product-specific string window:")
    for m in ASCII_RE.finditer(data):
        if 0xC7600 <= m.start() <= 0xC8600:
            print(f"  off=0x{m.start():06X} addr=0x{BASE+m.start():08X} {m.group().decode('ascii')}")

    md = Cs(CS_ARCH_ARM, CS_MODE_ARM | CS_MODE_LITTLE_ENDIAN)
    md.detail = True
    md_thumb = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN)
    md_thumb.detail = True
    instructions = list(md.disasm(data[: len(data) & ~3], BASE))
    pc_literal_refs: dict[int, list] = {}
    for insn in instructions:
        for op in insn.operands:
            if op.type == ARM_OP_MEM and op.mem.base == ARM_REG_PC:
                literal_addr = (insn.address + 8 + op.mem.disp) & 0xFFFFFFFF
                pc_literal_refs.setdefault(literal_addr, []).append(insn)

    print("\nString pointer references and nearby code:")
    for target in TARGETS:
        string_off = data.find(target)
        if string_off < 0:
            print(f"\n{target!r}: NOT FOUND")
            continue
        string_addr = BASE + string_off
        pointer_offsets = []
        for pointer in (string_addr, string_addr | 1):
            needle = struct.pack("<I", pointer)
            start = 0
            while True:
                pos = data.find(needle, start)
                if pos < 0:
                    break
                pointer_offsets.append(pos)
                start = pos + 1
        print(f"\n{target.decode()!r} off=0x{string_off:X} addr=0x{string_addr:X}")
        if not pointer_offsets:
            print("  no absolute pointer words found")
            continue
        for pointer_off in sorted(set(pointer_offsets)):
            pointer_addr = BASE + pointer_off
            print(f"  pointer word off=0x{pointer_off:X} addr=0x{pointer_addr:X}")
            refs = pc_literal_refs.get(pointer_addr, [])
            thumb_refs = []
            scan_start = max(0, pointer_off - 0x1000) & ~1
            for insn_off in range(scan_start, pointer_off, 2):
                decoded = list(
                    md_thumb.disasm(data[insn_off : insn_off + 4], BASE + insn_off, 1)
                )
                if not decoded:
                    continue
                candidate = decoded[0]
                for op in candidate.operands:
                    if op.type == ARM_OP_MEM and op.mem.base == ARM_REG_PC:
                        literal_addr = ((candidate.address + 4) & ~3) + op.mem.disp
                        if literal_addr == pointer_addr:
                            thumb_refs.append(candidate)
            if not refs and not thumb_refs:
                print("    no ARM/Thumb PC-relative LDR reference found")
                continue
            for ref in refs:
                print(f"    referenced by {render_insn(ref)}")
                start_addr = max(BASE, ref.address - 0x50) & ~3
                end_addr = min(BASE + len(data), ref.address + 0x70)
                for nearby in md.disasm(
                    data[start_addr - BASE : end_addr - BASE], start_addr
                ):
                    marker = ">" if nearby.address == ref.address else " "
                    print(f"      {marker} {render_insn(nearby)}")
            for ref in thumb_refs:
                print(f"    referenced by Thumb {render_insn(ref)}")
                start_addr = max(BASE, ref.address - 0x40) & ~1
                end_addr = min(BASE + len(data), ref.address + 0x60)
                for nearby in md_thumb.disasm(
                    data[start_addr - BASE : end_addr - BASE], start_addr
                ):
                    marker = ">" if nearby.address == ref.address else " "
                    print(f"      {marker} {render_insn(nearby)}")


if __name__ == "__main__":
    main()
