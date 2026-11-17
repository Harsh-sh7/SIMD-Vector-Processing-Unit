#!/usr/bin/env python3
"""
Mutation testing: inject one deliberate bug at a time into a COPY of the RTL and check that
the system testbench detects it (a "killed" mutant). A testbench that cannot fail proves nothing.
"""
import os, shutil, sys
from common import *

MUTANTS = [
    ("SRA behaves as logical shift",             "lane_alu.v", "y = sa >>> sh;", "y = a >> sh;"),
    ("signed LT treated as unsigned",            "lane_alu.v", "wire lt  = (sa <  sb);", "wire lt  = (a < b);"),
    ("SUB computes b-a",                         "lane_alu.v", "y = a - b;", "y = b - a;"),
    ("MAX returns the minimum",                  "lane_alu.v", "y = gt ? a : b;", "y = gt ? b : a;"),
    ("NE behaves like EQ",                       "lane_alu.v", "y = {W{~eq}};", "y = {W{eq}};"),
    ("shift amount taken from wrong bit slice",  "lane_alu.v", "b[SHW-1:0];", "b[SHW:1];"),
    ("MUL returns low half of ADD",              "lane_alu.v", "y = a * b;", "y = a + b;"),
    ("bypass removed on read port 1",            "vreg_file.v", "assign rd1 = byp1 ? wd : regs[ra1];", "assign rd1 = regs[ra1];"),
    ("bypass removed on read port 2",            "vreg_file.v", "assign rd2 = byp2 ? wd : regs[ra2];", "assign rd2 = regs[ra2];"),
    ("hazard unit compares wrong vs1 bits",      "vec_ctrl.v", "byp1    <= reg_we && (vd == instr_in[21:19]);", "byp1    <= reg_we && (vd == instr_in[20:18]);"),
    ("hazard unit ignores reg_we (false bypass)","vec_ctrl.v", "byp2    <= reg_we && (vd == instr_in[18:16]);", "byp2    <= (vd == instr_in[18:16]);"),
    ("VS form ignores scalar operand",           "vec_ctrl.v", "use_sc  <= (cls_n == `CLS_VS);", "use_sc  <= 1'b0;"),
    ("VLD does not write the register file",     "vec_ctrl.v", "wire       we_n    = alu_n || (cls_n == `CLS_VLD) || (cls_n == `CLS_VSPL);", "wire       we_n    = alu_n || (cls_n == `CLS_VSPL);"),
    ("lane B-operand MUX stuck on vector reg",   "simd_lane.v", "wire [W-1:0] b = use_sc ? sc : b_vec;", "wire [W-1:0] b = b_vec;"),
    ("compare predicate takes wrong lane bit",   "result_combiner.v", "assign mask[l] = lane_y[l*W];", "assign mask[l] = lane_y[l*W+1];"),
    ("ANY reduction implemented as ALL",         "result_combiner.v", "assign any_lane  = |mask;", "assign any_lane  = &mask;"),
    ("SSET writes zero",                         "simd_vpu.v", "sreg <= $signed(imm);", "sreg <= {W{1'b0}};"),
    ("VEXT always returns lane 0",               "simd_vpu.v", "if (imm == k) ext_val", "if (1'b0) ext_val"),
    ("store captures vs2 instead of vs1",        "simd_vpu.v", "if (st_en)  st_data <= rd1;", "if (st_en)  st_data <= rd2;"),
    ("instr_valid ignored (junk executes)",      "simd_vpu.v", ".instr_in(instr_valid ? instr : 32'd0)", ".instr_in(instr)"),
    ("external scalar write ignored",            "simd_vpu.v", "else if (scalar_we) sreg <= scalar_in;", "else if (1'b0) sreg <= scalar_in;"),
]

# Equivalent mutants: behaviourally identical to the original, so they MUST survive and are
# excluded from the score. ld_q is only consumed in the single cycle after a valid VLD, so
# dropping its clock-enable changes power, not function.
EQUIVALENT = [
    ("load-capture clock-enable removed (power only)", "simd_vpu.v", "else if (instr_valid) ld_q <= ld_data;", "else ld_q <= ld_data;"),
]


def main():
    mdir = os.path.join(BUILD, "mutant_rtl")
    killed, rows = 0, []
    for i, (name, fn, old, new) in enumerate(MUTANTS, 1):
        shutil.rmtree(mdir, ignore_errors=True)
        shutil.copytree(RTL, mdir)
        p = os.path.join(mdir, fn)
        src = open(p).read()
        if old not in src:
            sys.exit("mutation %d (%s): pattern not found in %s" % (i, name, fn))
        open(p, "w").write(src.replace(old, new, 1))
        ok, out = iverilog_run(os.path.join(TB, "tb_simd_vpu.v"), {"LANES": 4, "W": 16}, "mut", rtl_dir=mdir)
        detected = (not ok) or ("ALL TESTS PASSED" not in out)
        killed += detected
        rows.append((i, name, fn, "KILLED" if detected else "SURVIVED"))
        print("%2d  %-9s %-46s (%s)" % (i, rows[-1][3], name, fn), flush=True)
    eq_notes = []
    for name, fn, old, new in EQUIVALENT:
        shutil.rmtree(mdir, ignore_errors=True)
        shutil.copytree(RTL, mdir)
        p = os.path.join(mdir, fn)
        src = open(p).read()
        assert old in src, name
        open(p, "w").write(src.replace(old, new, 1))
        ok, out = iverilog_run(os.path.join(TB, "tb_simd_vpu.v"), {"LANES": 4, "W": 16}, "mut", rtl_dir=mdir)
        survived = ok and "ALL TESTS PASSED" in out
        eq_notes.append("EQUIVALENT mutant (%s): %s" % (name, "survived as expected" if survived else "UNEXPECTEDLY DETECTED"))
        print(eq_notes[-1])
    score = 100.0 * killed / len(MUTANTS)
    summary = "Mutation score: %d / %d mutants killed (%.1f %%)" % (killed, len(MUTANTS), score)
    print(summary)
    with open(os.path.join(RESULTS, "mutation_report.txt"), "w") as f:
        f.write("#  result    mutation                                        file\n")
        for r in rows:
            f.write("%2d %-9s %-46s %s\n" % (r[0], r[3], r[1], r[2]))
        f.write("\n" + summary + "\n")
        for n in eq_notes:
            f.write(n + "\n")
    shutil.rmtree(mdir, ignore_errors=True)
    sys.exit(0 if killed == len(MUTANTS) else 1)


if __name__ == "__main__":
    main()

# note: outputs under results/; re-run after any RTL change
