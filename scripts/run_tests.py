#!/usr/bin/env python3
"""Run the full regression: exhaustive lane-ALU test + system testbench over several (LANES, W)."""
import os, re, sys
from common import *

CONFIGS = [(1, 16), (2, 16), (4, 16), (8, 16), (4, 8), (4, 32), (8, 8), (16, 16)]


def main():
    lines, ok_all = [], True
    ok, out = iverilog_run(os.path.join(TB, "tb_lane_alu.v"), {"W": 8}, "lane_alu")
    open(os.path.join(LOGS, "tb_lane_alu.log"), "w").write(out)
    m = re.search(r"(\d+) checks, (\d+) errors", out)
    passed = ok and "EXHAUSTIVE TEST PASSED" in out
    ok_all &= passed
    lines.append(("lane ALU exhaustive (W=8)", "%s checks / %s errors" % (m.group(1), m.group(2)) if m else "?", passed))

    for lanes, w in CONFIGS:
        ok, out = iverilog_run(os.path.join(TB, "tb_simd_vpu.v"), {"LANES": lanes, "W": w}, "sys_%d_%d" % (lanes, w))
        open(os.path.join(LOGS, "tb_simd_vpu_L%d_W%d.log" % (lanes, w)), "w").write(out)
        passed = ok and ("ALL TESTS PASSED (LANES=%d, W=%d)" % (lanes, w)) in out
        m = re.search(r"instructions issued: (\d+)\s+stores checked: (\d+)\s+extracts checked: (\d+)\s+flag updates checked: (\d+)", out)
        det = "%s instr, %s stores, %s extracts, %s flag checks" % m.groups() if m else "compile/run error"
        ok_all &= passed
        lines.append(("system TB  LANES=%d W=%d" % (lanes, w), det, passed))

    for w in (8, 16):
        fn = os.path.join(ROOT, "vectors", "vectors_L4_W%d.mem" % w)
        if not os.path.exists(fn):
            run(["python3", os.path.join(ROOT, "scripts", "gen_dls_vectors.py"), "--lanes", "4", "--width", str(w)], check=True)
        ok, out = iverilog_run(os.path.join(TB, "tb_vectors.v"), {"LANES": 4, "W": w, "FILE": '"vectors/vectors_L4_W%d.mem"' % w}, "vec_%d" % w)
        open(os.path.join(LOGS, "tb_vectors_W%d.log" % w), "w").write(out)
        passed = ok and "VECTOR REPLAY PASSED" in out
        m = re.search(r"(\d+) vectors replayed, (\d+) checked, (\d+) errors", out)
        ok_all &= passed
        lines.append(("golden-vector replay W=%d" % w, "%s vectors / %s errors" % (m.group(1), m.group(3)) if m else "error", passed))

    out = os.path.join(BUILD, "dlsm_reg.vvp")
    rc, txt = run(["iverilog", "-g2012", "-I", RTL, "-o", out, os.path.join(TB, "tb_dls_mirror.v")] +
                  sorted(os.path.join(ROOT, "dls_rtl", f) for f in os.listdir(os.path.join(ROOT, "dls_rtl")) if f.endswith(".v")) + [os.path.join(RTL, "lane_alu.v")])
    if rc == 0:
        rc, txt = run(["vvp", out])
    open(os.path.join(LOGS, "tb_dls_mirror.log"), "w").write(txt)
    passed = "DLS MIRROR TESTS PASSED" in txt
    ok_all &= passed
    lines.append(("DLS-chip mirror (dls_rtl)", "screenshot cases + 524,288 ALU + 393,216 equiv. + 4,000 streaming", passed))

    width = max(len(l[0]) for l in lines)
    txt = ["%-*s  %-60s %s" % (width, n, d, "PASS" if p else "FAIL") for n, d, p in lines]
    txt.append("")
    txt.append("REGRESSION %s" % ("PASSED" if ok_all else "FAILED"))
    print("\n".join(txt))
    open(os.path.join(RESULTS, "regression_summary.txt"), "w").write("\n".join(txt) + "\n")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()

# note: outputs under results/; re-run after any RTL change
