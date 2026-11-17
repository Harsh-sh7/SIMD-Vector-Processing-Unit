#!/usr/bin/env python3
"""
Everything for the Digital-Logic-Sim-style design (dls_rtl/): tests, mutation check, scalar-vs-SIMD cycles,
FPGA resources and Fmax.  Writes results/dls_mirror_*.csv and results/DLS_MIRROR_RESULTS.md.
"""
import concurrent.futures as cf, csv, os, re, shutil, sys
from common import *

DLS = os.path.join(ROOT, "dls_rtl")
SEEDS = [1, 2, 3, 4]
LANES_LIST = [1, 2, 4, 8, 16]


def dls_files(d=DLS):
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".v"))


def sim_tests(d=DLS, tag="dlsm"):
    out = os.path.join(BUILD, tag + ".vvp")
    rc, txt = run(["iverilog", "-g2012", "-I", RTL, "-o", out, os.path.join(TB, "tb_dls_mirror.v")] + dls_files(d) + [os.path.join(RTL, "lane_alu.v")])
    if rc != 0:
        return False, txt
    rc, txt = run(["vvp", out])
    return "DLS MIRROR TESTS PASSED" in txt, txt


MUTANTS = [
    ("subtractor: carry-in 1 -> 0 (a + ~b instead of a - b)", "subtractor8.v", ".cin(1'b1)", ".cin(1'b0)"),
    ("full adder: carry-propagate term dropped",               "full_adder.v", "(a & b) | (cin & (a ^ b))", "(a & b)"),
    ("mux: select 3 returns input 2",                          "mux8to1_8bit.v", "3'd3: y = d3;", "3'd3: y = d2;"),
    ("compare: equality turned into inequality",               "compare8.v", "(a == b)", "(a != b)"),
    ("1BIT-8BIT: true gives 1 instead of 255",                 "compare8.v", "{8{bit_in}}", "{7'b0, bit_in}"),
    ("ALU: XOR result wired to the OR input",                  "alu8.v", ".d3(r_or),\n                        .d4(r_xor)", ".d3(r_or),\n                        .d4(r_or)"),
    ("register ignores its enable",                            "registers.v", "if (en) q <= d;", "q <= d;"),
    ("vector register file: B bank loaded with load_a",        "register_files.v", ".en(load_b)", ".en(load_a)"),
    ("opcode 5 not connected (output 0)",                      "alu8.v", ".d5(r_cmp)", ".d5(8'h00)"),
]


def mutation():
    res = []
    for name, fn, old, new in MUTANTS:
        d = os.path.join(BUILD, "dls_mut")
        shutil.rmtree(d, ignore_errors=True); shutil.copytree(DLS, d)
        src = open(os.path.join(d, fn)).read()
        if old not in src:
            sys.exit("mutation pattern missing: %s / %s" % (name, fn))
        open(os.path.join(d, fn), "w").write(src.replace(old, new, 1))
        ok, _ = sim_tests(d, "dlsmut")
        res.append((name, fn, "KILLED" if not ok else "SURVIVED"))
        print("  %-9s %s" % (res[-1][2], name), flush=True)
    shutil.rmtree(os.path.join(BUILD, "dls_mut"), ignore_errors=True)
    return res


def perf():
    rows = []
    for l in LANES_LIST:
        out = os.path.join(BUILD, "dlsperf_%d.vvp" % l)
        rc, txt = run(["iverilog", "-g2012", "-Ptb_dls_perf.LANES=%d" % l, "-o", out, os.path.join(TB, "tb_dls_perf.v")] + dls_files())
        rc, txt = run(["vvp", out])
        m = re.search(r"DLSPERF,(\d+),(\d+),(\d+),(\d+),(\d+)", txt)
        if not m or m.group(5) != "1":
            sys.exit("dls perf failed for lanes %d\n%s" % (l, txt))
        rows.append(dict(lanes=int(m.group(1)), n=int(m.group(2)), cycles=int(m.group(3)), passes=int(m.group(4))))
        print("  lanes %-2d  cycles %-3d  passes %d" % (l, rows[-1]["cycles"], rows[-1]["passes"]), flush=True)
    return rows


def yosys_res(lanes, flow):
    stat = os.path.join(LOGS, "dls_%s_L%d.stat" % (flow, lanes))
    synth = "synth_ice40 -top simd_lanes" if flow == "ice40" else "synth_xilinx -family xc7 -flatten -top simd_lanes"
    script = "read_verilog %s; chparam -set LANES %d simd_lanes; %s; tee -o %s stat" % (" ".join(dls_files()), lanes, synth, stat)
    run(["yosys", "-p", script], log=os.path.join(LOGS, "dls_%s_L%d.log" % (flow, lanes)), check=True)
    cells = {}
    for line in open(stat):
        m = re.match(r"\s+(\d+)\s+(\$?[A-Za-z_0-9]+)\s*$", line)
        if m: cells[m.group(2)] = int(m.group(1))
    if flow == "ice40":
        return dict(lut=cells.get("SB_LUT4", 0), ff=sum(v for k, v in cells.items() if k.startswith("SB_DFF")), carry=cells.get("SB_CARRY", 0))
    return dict(lut=sum(v for k, v in cells.items() if re.fullmatch(r"LUT[1-6]", k)), ff=sum(v for k, v in cells.items() if re.fullmatch(r"FD[A-Z]*E?", k)), carry=cells.get("CARRY4", 0))


def pnr(lanes):
    js = os.path.join(BUILD, "dlsb_L%d.json" % lanes)
    script = "read_verilog %s %s; chparam -set LANES %d bench_top_dls; synth_ice40 -top bench_top_dls -json %s" % (
        " ".join(dls_files()), os.path.join(SYNTH, "bench_top_dls.v"), lanes, js)
    run(["yosys", "-q", "-p", script], log=os.path.join(LOGS, "dlsb_L%d_yosys.log" % lanes), check=True)

    def one(seed):
        rc, out = run(["nextpnr-ice40", "--hx8k", "--package", "ct256", "--json", js, "--freq", "150", "--seed", str(seed)],
                      log=os.path.join(LOGS, "dlsb_L%d_seed%d.log" % (lanes, seed)))
        fm = re.findall(r"Max frequency for clock '[^']*': ([0-9.]+) MHz", out)
        return float(fm[-1]) if fm else None
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        vals = sorted(v for v in ex.map(one, SEEDS) if v)
    return max(vals), vals[len(vals) // 2]


def main():
    quick = "--quick" in sys.argv          # tests + mutation + cycle counts only (no synthesis, no files written)
    print("== simulation tests =="); ok, txt = sim_tests()
    open(os.path.join(LOGS, "tb_dls_mirror.log"), "w").write(txt)
    print("\n".join(l for l in txt.splitlines() if "MATCH" in l or "PASSED" in l or "FAILED" in l or "checks" in l))
    if not ok: sys.exit("DLS mirror tests failed")
    print("== mutation check =="); mut = mutation()
    killed = sum(1 for m in mut if m[2] == "KILLED")
    print("== cycle counts =="); pf = perf()
    if quick:
        print("Scalar (1 lane) %d cycles vs 4 lanes %d cycles for 64 elements = %.2fx" % (pf[0]["cycles"], pf[2]["cycles"], pf[0]["cycles"] / pf[2]["cycles"]))
        return
    print("== resources ==")
    res = []
    for l in (1, 2, 4, 8, 16):
        for flow in ("ice40", "xc7"):
            r = yosys_res(l, flow); r.update(lanes=l, flow=flow); res.append(r); print(" ", r, flush=True)
    print("== Fmax (HX8K) ==")
    fmax = {}
    for l in (1, 2, 4, 8):
        fmax[l] = pnr(l); print("  lanes", l, fmax[l], flush=True)

    with open(os.path.join(RESULTS, "dls_mirror_resources.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["flow", "lanes", "lut", "ff", "carry"]); w.writeheader(); w.writerows(res)
    with open(os.path.join(RESULTS, "dls_mirror_perf.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["lanes", "n", "cycles", "passes"]); w.writeheader(); w.writerows(pf)
    with open(os.path.join(RESULTS, "dls_mirror_fmax.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["lanes", "fmax_best_mhz", "fmax_median_mhz"])
        for l, (b, m) in fmax.items(): w.writerow([l, b, m])

    c1 = pf[0]["cycles"]
    L = ["# DLS-style design (dls_rtl/) - measured results\n",
         "Generated by `scripts/run_dls_mirror.py`. Design = VECTOR-REGISTER-FILE -> LANES x 8-Bit-ALU -> RESULT-REGISTER-FILE, 8-bit lanes, 3-bit opcode (6 operations).\n",
         "## Tests\n", "* Screenshot cases (6 ALU operations + full-chip vector subtract), exhaustive ALU (524,288 checks), equivalence with `rtl/lane_alu.v` (393,216 checks), 4,000-pass streaming test, enable-gating test: **all pass**.",
         "* Mutation check: **%d / %d** injected bugs detected.\n" % (killed, len(mut)),
         "| # | Injected bug | File | Result |", "|---|---|---|---|"]
    for i, m in enumerate(mut, 1): L.append("| %d | %s | %s | %s |" % (i, m[0], m[1], m[2]))
    L += ["\n## Scalar (1 lane) vs SIMD - cycles for N = 64 elements, opcode changing every pass, streaming mode\n",
          "| Lanes | Passes | Cycles | Speed-up | Efficiency | Elements/cycle |", "|---:|---:|---:|---:|---:|---:|"]
    for r in pf:
        L.append("| %d | %d | %d | %.2fx | %.0f %% | %.2f |" % (r["lanes"], r["passes"], r["cycles"], c1 / r["cycles"], 100 * c1 / r["cycles"] / r["lanes"], r["n"] / r["cycles"]))
    L.append("\nCycles = passes + 2 (one clock to load the operand registers, one to capture the result). Run the DLS way (enables pulsed by hand) a pass costs 2 clocks, so the speed-up is exactly the lane count.\n")
    L += ["## FPGA resources (Yosys, core `simd_lanes`)\n", "| Lanes | iCE40 LUT4 | iCE40 FF | Xilinx-7 LUT | Xilinx-7 FF |", "|---:|---:|---:|---:|---:|"]
    for l in (1, 2, 4, 8, 16):
        a = [r for r in res if r["lanes"] == l and r["flow"] == "ice40"][0]; b = [r for r in res if r["lanes"] == l and r["flow"] == "xc7"][0]
        L.append("| %d | %d | %d | %d | %d |" % (l, a["lut"], a["ff"], b["lut"], b["ff"]))
    L += ["\n## Maximum frequency (nextpnr, iCE40 HX8K, best of 4 seeds)\n", "| Lanes | Fmax best (MHz) | Fmax median (MHz) | Wall-clock speed-up vs 1 lane (64 elements) |", "|---:|---:|---:|---:|"]
    t1 = pf[0]["cycles"] / fmax[1][0]
    for l, (b, m) in fmax.items():
        cyc = [r for r in pf if r["lanes"] == l][0]["cycles"]
        L.append("| %d | %.1f | %.1f | %.2fx |" % (l, b, m, t1 / (cyc / b)))
    open(os.path.join(RESULTS, "DLS_MIRROR_RESULTS.md"), "w").write("\n".join(L) + "\n")
    print("wrote results/DLS_MIRROR_RESULTS.md")


if __name__ == "__main__":
    main()

# note: outputs under results/; re-run after any RTL change
