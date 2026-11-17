#!/usr/bin/env python3
"""Scalar-vs-SIMD cycle-count benchmark: 3 kernels x lane counts, results verified by tb_perf.v."""
import csv, os, re, sys
from common import *

KERNELS = {0: "mixed kernel (5 ALU ops/chunk)", 1: "vector add", 2: "min-select via compare mask"}
LANES = [1, 2, 4, 8, 16]
N = 64


def main():
    rows, ok_all = [], True
    for k in KERNELS:
        for l in LANES:
            ok, out = iverilog_run(os.path.join(TB, "tb_perf.v"), {"LANES": l, "KERNEL": k, "N": N, "W": 16}, "perf_%d_%d" % (k, l))
            m = re.search(r"^PERF,(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)", out, re.M)
            if not (ok and m):
                sys.exit("perf run failed (kernel %d lanes %d):\n%s" % (k, l, out))
            kk, ll, w, n, cyc, instr, laneops, issued, passed = map(int, m.groups())
            ok_all &= bool(passed)
            rows.append(dict(kernel=kk, lanes=ll, w=w, n=n, cycles=cyc, instr=instr, lane_ops=laneops, correct=passed))
            print("kernel %d  lanes %-2d  cycles %-4d  instr %-4d  lane-ops %-4d  %s" %
                  (kk, ll, cyc, instr, laneops, "OK" if passed else "WRONG"))
    with open(os.path.join(RESULTS, "perf_cycles.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader(); wr.writerows(rows)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()

# note: outputs under results/; re-run after any RTL change
