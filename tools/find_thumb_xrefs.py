from __future__ import annotations

import argparse
import struct
from pathlib import Path

from capstone import CS_ARCH_ARM, CS_MODE_LITTLE_ENDIAN, CS_MODE_THUMB, Cs
from capstone.arm import ARM_OP_IMM, ARM_OP_MEM, ARM_REG_PC


BASE = 0x10000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("target", nargs="+", type=lambda x: int(x, 0))
    args = parser.parse_args()
    data = args.image.read_bytes()
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN)
    md.detail = True

    for target in args.target:
        print(f"target=0x{target:X}")
        needle = struct.pack("<I", target)
        pointer_offsets: list[int] = []
        start = 0
        while True:
            off = data.find(needle, start)
            if off < 0:
                break
            pointer_offsets.append(off)
            start = off + 1
        for off in pointer_offsets:
            pool_addr = BASE + off
            print(f"  pointer word at 0x{pool_addr:X}")
            scan_start = max(0, off - 0x1000) & ~1
            for insn_off in range(scan_start, off, 2):
                decoded = list(md.disasm(data[insn_off : insn_off + 4], BASE + insn_off, 1))
                if not decoded:
                    continue
                insn = decoded[0]
                for op in insn.operands:
                    if op.type == ARM_OP_MEM and op.mem.base == ARM_REG_PC:
                        literal_addr = ((insn.address + 4) & ~3) + op.mem.disp
                        if literal_addr == pool_addr:
                            print(f"    literal xref 0x{insn.address:X}: {insn.mnemonic} {insn.op_str}")
        # Brute-force direct branch/call references, decoding at every halfword.
        for off in range(0, len(data) - 4, 2):
            decoded = list(md.disasm(data[off : off + 4], BASE + off, 1))
            if not decoded:
                continue
            insn = decoded[0]
            if not insn.mnemonic.startswith("b"):
                continue
            if any(op.type == ARM_OP_IMM and op.imm == target for op in insn.operands):
                print(f"  branch xref 0x{insn.address:X}: {insn.mnemonic} {insn.op_str}")


if __name__ == "__main__":
    main()
