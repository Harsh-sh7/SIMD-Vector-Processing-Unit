#!/usr/bin/env python3
"""
Golden test-vector generator for cross-checking the Verilog RTL against the Digital Logic Sim (DLS)
SIMD_4LANE chip.

  python3 scripts/gen_dls_vectors.py --lanes 4 --width 8        # writes vectors/*.mem and a printable *.md sheet
  make vectors                                                   # regenerate both widths and replay them through the RTL

* vectors/vectors_L<L>_W<W>.mem  : $readmemh file used by tb/tb_vectors.v (op, A, B, expected per test; RTL op codes)
* vectors/DLS_TEST_SHEET_L4_W8.md : printable sheet for the DLS chip (4 lanes x 8 bit). Only the six operations the
                                    chip has, with the DLS opcode (S2 S1 S0) and unsigned decimal values as DLS shows them.
* vectors/RTL_TEST_SHEET_L<L>_W<W>.md : printable sheet for any other size (all 16 generalised-RTL operations, RTL op codes).

The reference model below is written independently of the Verilog; tb_vectors.v proves both agree.
"""
import argparse, os, random

OPS = ["ADD", "SUB", "AND", "OR", "XOR", "SLL", "SRL", "SRA", "MUL", "EQ", "NE", "LT", "GT", "LTU", "MIN", "MAX"]

# The DLS 8-Bit-ALU has six operations. Its opcode is NOT the RTL op code for COMPARE:
# DLS 101 = COMPARE (equality) = RTL EQ (code 9). Opcodes 110 / 111 are unconnected in the chip.
DLS_OPS = [("ADD", "ADD", "000"), ("SUB", "SUB", "001"), ("AND", "AND", "010"),
           ("OR", "OR", "011"), ("XOR", "XOR", "100"), ("EQ", "COMPARE", "101")]   # (RTL name, DLS name, opcode)
DLS_LANES, DLS_WIDTH = 4, 8

# Extra DLS-only rows: the screenshot case and COMPARE with equal lanes (the generated vectors almost never
# contain equal operands). Computed with the same reference model; not part of the .mem replay.
DLS_EXTRA = [("SUB", [10, 20, 30, 40], [1, 2, 3, 4]),          # SIMD_4LANE screenshot: 9, 18, 27, 36
             ("ADD", [10, 20, 30, 40], [1, 2, 3, 4]),
             ("EQ", [112, 5, 255, 0], [112, 6, 255, 1]),
             ("EQ", [64, 96, 128, 200], [64, 96, 128, 200])]


def ref(op, a, b, w):
    m = (1 << w) - 1
    sa = a - (1 << w) if a >> (w - 1) else a
    sb = b - (1 << w) if b >> (w - 1) else b
    sh = b % w
    ones = m
    r = {
        "ADD": a + b, "SUB": a - b, "AND": a & b, "OR": a | b, "XOR": a ^ b,
        "SLL": a << sh, "SRL": a >> sh, "SRA": sa >> sh, "MUL": a * b,
        "EQ": ones if a == b else 0, "NE": ones if a != b else 0,
        "LT": ones if sa < sb else 0, "GT": ones if sa > sb else 0, "LTU": ones if a < b else 0,
        "MIN": a if sa < sb else b, "MAX": a if sa > sb else b,
    }[op]
    return r & m


def corners(w):
    m = (1 << w) - 1
    return [0, 1, m, 1 << (w - 1), (1 << (w - 1)) - 1, 0x55 & m, 0xAA & m, w - 1, 2]


def signed(v, w):
    return v - (1 << w) if v >> (w - 1) else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lanes", type=int, default=4)
    ap.add_argument("--width", type=int, default=8)
    ap.add_argument("--seed", type=int, default=2024)
    ap.add_argument("--per-op", type=int, default=12)
    ap.add_argument("--ops", default="", help="comma list, e.g. ADD,SUB,AND,OR: write ONLY a custom sheet for the operations your DLS ALU has")
    args = ap.parse_args()
    L, W = args.lanes, args.width
    rnd = random.Random(args.seed)
    cs = corners(W)
    m = (1 << W) - 1
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vectors")
    os.makedirs(out, exist_ok=True)
    tag = "L%d_W%d" % (L, W)

    is_dls = (L == DLS_LANES and W == DLS_WIDTH)
    dls_name = {rtl: dls for rtl, dls, _ in DLS_OPS}
    dls_code = {rtl: code for rtl, _, code in DLS_OPS}
    custom = []
    for o in (x.strip().upper() for x in args.ops.split(",") if x.strip()):
        o = "EQ" if o == "COMPARE" else o
        if o not in dls_code:
            raise SystemExit("--ops: %s is not an operation of the DLS chip (choose from ADD,SUB,AND,OR,XOR,COMPARE)" % o)
        custom.append(o)
    if custom and not is_dls:
        raise SystemExit("--ops writes a DLS sheet; the DLS chip is %d lanes x %d bit" % (DLS_LANES, DLS_WIDTH))

    # all 16 operations are always generated, so the sheet rows are the same tests as in the .mem file
    tests = []
    for oi, op in enumerate(OPS):
        for k in range(args.per_op):
            if k < 6:       # directed: lane l gets corner (k + l), operand B lane gets a different corner
                a = [cs[(k + l) % len(cs)] for l in range(L)]
                b = [cs[(k * 2 + l + 3) % len(cs)] for l in range(L)]
            else:           # random
                a = [rnd.randint(0, m) for _ in range(L)]
                b = [rnd.randint(0, m) for _ in range(L)]
            r = [ref(op, a[l], b[l], W) for l in range(L)]
            tests.append((oi, op, k, a, b, r))

    vw = (L * W + 3) // 4              # hex digits of the packed vector

    def pack(lanes):
        v = 0
        for l, x in enumerate(lanes):
            v |= x << (l * W)
        return v

    if not custom:
      with open(os.path.join(out, "vectors_%s.mem" % tag), "w") as f:
        f.write("// op  A  B  expected   (packed, lane 0 = least-significant lane)  generated by gen_dls_vectors.py\n")
        for oi, op, k, a, b, r in tests:
            f.write("%x %0*x %0*x %0*x\n" % (oi, vw, pack(a), vw, pack(b), vw, pack(r)))

    if is_dls:
        sheet = os.path.join(out, "DLS_TEST_SHEET_%s%s.md" % (tag, "_custom" if custom else ""))
        ops = custom or [rtl for rtl, _, _ in DLS_OPS]
        dec = lambda v: ", ".join("%d" % x for x in v)
        with open(sheet, "w") as f:
            f.write("# DLS cross-check sheet: SIMD_4LANE (4 lanes x 8 bit)\n\n")
            f.write("For the Digital Logic Sim chip `SIMD_4LANE`. Set A0..A3 and B0..B3, put the opcode S2 S1 S0 on the "
                    "low three bits of `IN` (the fourth bit is unused), pulse `LOAD-A` / `LOAD-B` with a clock, then "
                    "`RESULT_WRITE` with a clock, and compare R0..R3 with the EXPECTED column.\n\n")
            f.write("Values are unsigned decimal, as the simulator displays them, listed lane 0 first (A0, A1, A2, A3). "
                    "COMPARE gives 255 when the two lanes are equal and 0 otherwise. Opcodes 110 / 111 are unconnected.\n\n")
            f.write("The rows of the first table are tests from `vectors_L4_W8.mem`, which `make vectors` "
                    "replays through the Verilog RTL (where COMPARE is the RTL operation EQ, code 9).\n\n")
            f.write("| # | Operation | Opcode (S2 S1 S0) | A0..A3 | B0..B3 | EXPECTED R0..R3 | DLS result | OK? |\n"
                    "|---|---|:---:|---|---|---|---|---|\n")
            n = 0
            for oi, op, k, a, b, r in tests:
                if op not in ops or k not in (0, 1, 2, 3, 4, 7, 9):
                    continue
                n += 1
                f.write("| %d | %s | `%s` | %s | %s | %s |  |  |\n" % (n, dls_name[op], dls_code[op], dec(a), dec(b), dec(r)))
            extra = [(op, a, b) for op, a, b in DLS_EXTRA if op in ops]
            if extra:
                f.write("\n## Screenshot and equality cases (DLS only, not in the .mem replay)\n\n")
                f.write("| # | Operation | Opcode (S2 S1 S0) | A0..A3 | B0..B3 | EXPECTED R0..R3 | DLS result | OK? |\n"
                        "|---|---|:---:|---|---|---|---|---|\n")
                for op, a, b in extra:
                    n += 1
                    r = [ref(op, a[l], b[l], W) for l in range(L)]
                    f.write("| %d | %s | `%s` | %s | %s | %s |  |  |\n" % (n, dls_name[op], dls_code[op], dec(a), dec(b), dec(r)))
    else:
        sheet = os.path.join(out, "RTL_TEST_SHEET_%s.md" % tag)
        hx = (W + 3) // 4
        with open(sheet, "w") as f:
            f.write("# Generalised-RTL cross-check sheet  (%d lanes x %d bit)\n\n" % (L, W))
            f.write("For the generalised Verilog core (`rtl/`). The DLS chip is 4 lanes x 8 bit with six operations, so these "
                    "rows cannot be keyed into it; use `DLS_TEST_SHEET_L4_W8.md` for the simulator. "
                    "Op codes are the RTL codes. Values are hex (lane 0 = least-significant lane); the signed decimal of "
                    "the result is in brackets. The same vectors are replayed through the RTL by `make vectors`.\n\n")
            f.write("Shift ops use the shift amount `B mod %d` (low %d bits of B). Compare ops return all-ones (true) or 0 (false) per lane.\n\n" % (W, (W - 1).bit_length()))
            f.write("| # | Op (RTL code) | A (L%d..L0) | B (L%d..L0) | EXPECTED (L%d..L0) | Result | OK? |\n|---|---|---|---|---|---|---|\n" % ((L - 1,) * 3))
            n = 0
            for oi, op, k, a, b, r in tests:
                if k not in (0, 1, 2, 7):      # a short printable selection: first 3 directed + 1 random per op
                    continue
                n += 1
                fa = " ".join("%0*X" % (hx, x) for x in reversed(a))
                fb = " ".join("%0*X" % (hx, x) for x in reversed(b))
                fr = " ".join("%0*X(%d)" % (hx, x, signed(x, W)) for x in reversed(r))
                f.write("| %d | %s (%X) | %s | %s | %s |  |  |\n" % (n, op, oi, fa, fb, fr))
    print("wrote %d vectors for %s into %s (sheet: %s)" % (len(tests), tag, out, os.path.basename(sheet)))


if __name__ == "__main__":
    main()

# note: outputs under results/; re-run after any RTL change
