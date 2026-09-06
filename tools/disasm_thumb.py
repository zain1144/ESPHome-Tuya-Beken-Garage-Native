from __future__ import annotations

import argparse
import struct
from pathlib import Path

from capstone import CS_ARCH_ARM, CS_MODE_LITTLE_ENDIAN, CS_MODE_THUMB, Cs
from capstone.arm import ARM_OP_MEM, ARM_REG_PC


BASE = 0x10000


def printable_string(data: bytes, address: int) -> str | None:
    offset = address - BASE
    if not 0 <= offset < len(data):
        return None
    end = offset
    while end < len(data) and 0x20 <= data[end] <= 0x7E:
        end += 1
    if end - offset < 4:
        return None
    return data[offset:end].decode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("start", type=lambda x: int(x, 0))
    parser.add_argument("end", type=lambda x: int(x, 0))
    args = parser.parse_args()
    data = args.image.read_bytes()
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN)
    md.detail = True
    start = args.start
    end = args.end
    block = data[start - BASE : end - BASE]
    for insn in md.disasm(block, start):
        annotation = ""
        for op in insn.operands:
            if op.type == ARM_OP_MEM and op.mem.base == ARM_REG_PC:
                pool_addr = ((insn.address + 4) & ~3) + op.mem.disp
                pool_off = pool_addr - BASE
                if 0 <= pool_off <= len(data) - 4:
                    value = struct.unpack_from("<I", data, pool_off)[0]
                    string = printable_string(data, value)
                    annotation = f" ; [0x{pool_addr:X}]=0x{value:X}"
                    if string:
                        annotation += f" -> {string!r}"
        print(f"0x{insn.address:08X}: {insn.bytes.hex():10s} {insn.mnemonic:8s} {insn.op_str}{annotation}")


if __name__ == "__main__":
    main()
