#!/usr/bin/env python3
"""Turn the CSV results into figures (docs/img) and a markdown table file (results/RESULTS.md)."""
import csv, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import RESULTS, ROOT

IMG = os.path.join(ROOT, "docs", "img")
os.makedirs(IMG, exist_ok=True)
KNAME = {0: "Mixed kernel (8 instr/chunk, 5 ALU)", 1: "Vector add (4 instr/chunk, 1 ALU)", 2: "Min-select via mask (7 instr/chunk, 4 ALU)"}
COL = {0: "#1f77b4", 1: "#2ca02c", 2: "#d9822b"}


def rd(name):
    with open(os.path.join(RESULTS, name)) as f:
        return list(csv.DictReader(f))


perf = rd("perf_cycles.csv")
res = rd("synth_resources.csv")
fmax = rd("synth_fmax.csv")
cmp_ = rd("fmax_v1_vs_v2.csv")

cyc = {(int(r["kernel"]), int(r["lanes"])): int(r["cycles"]) for r in perf}
lops = {(int(r["kernel"]), int(r["lanes"])): int(r["lane_ops"]) for r in perf}
N = int(perf[0]["n"])
LANES = sorted({int(r["lanes"]) for r in perf})
fm = {(r["device"], int(r["lanes"]), int(r["w"])): float(r["fmax_best"]) for r in fmax if r["fmax_best"]}
rs = {(r["flow"], int(r["lanes"]), int(r["w"])): r for r in res}


def speedup(k, l):
    return cyc[(k, 1)] / cyc[(k, l)]


# ------------------------------------------------------------ figure 1: cycles and speed-up
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for k in KNAME:
    ax[0].plot(LANES, [cyc[(k, l)] for l in LANES], "o-", color=COL[k], label=KNAME[k])
ax[0].set_xscale("log", base=2); ax[0].set_yscale("log", base=2)
ax[0].set_xticks(LANES); ax[0].set_xticklabels(LANES)
ax[0].set_xlabel("lanes (1 = scalar baseline)"); ax[0].set_ylabel("total cycles for %d elements" % N)
ax[0].set_title("Cycle count, same program"); ax[0].grid(alpha=0.3, which="both"); ax[0].legend(fontsize=7)
for k in KNAME:
    ax[1].plot(LANES, [speedup(k, l) for l in LANES], "o-", color=COL[k], label=KNAME[k])
ax[1].plot(LANES, LANES, "k--", lw=1, label="ideal (= lanes)")
ax[1].set_xscale("log", base=2); ax[1].set_yscale("log", base=2)
ax[1].set_xticks(LANES); ax[1].set_xticklabels(LANES); ax[1].set_yticks(LANES); ax[1].set_yticklabels(LANES)
ax[1].set_xlabel("lanes"); ax[1].set_ylabel("speed-up vs scalar (cycles)")
ax[1].set_title("Cycle speed-up"); ax[1].grid(alpha=0.3, which="both"); ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(os.path.join(IMG, "speedup.png"), dpi=180); plt.close(fig)

# ------------------------------------------------------------ figure 2: resources
fig, ax = plt.subplots(1, 3, figsize=(12, 3.8))
Ls = [1, 2, 4, 8]
for flow, lab, c in (("ice40", "iCE40 (LUT multipliers)", "#1f77b4"), ("ice40dsp", "iCE40 + DSP multipliers", "#2ca02c"), ("xc7", "Xilinx 7-series estimate", "#d9822b")):
    ax[0].plot(Ls, [int(rs[(flow, l, 16)]["lut"]) for l in Ls], "o-", color=c, label=lab)
ax[0].axhline(7680, color="#1f77b4", ls=":", lw=1); ax[0].text(1, 7800, "HX8K capacity (7680 LUT4)", fontsize=6.5, color="#1f77b4")
ax[0].axhline(5280, color="#2ca02c", ls=":", lw=1); ax[0].text(1, 5400, "UP5K capacity (5280 LUT4)", fontsize=6.5, color="#2ca02c")
ax[0].set_xlabel("lanes (W = 16)"); ax[0].set_ylabel("LUTs"); ax[0].set_title("LUT usage"); ax[0].grid(alpha=0.3); ax[0].legend(fontsize=6.5)
ax[0].set_xticks(Ls)
ax[1].plot(Ls, [int(rs[("ice40", l, 16)]["ff"]) for l in Ls], "o-", color="#7f4fb0")
ax[1].set_xlabel("lanes (W = 16)"); ax[1].set_ylabel("flip-flops"); ax[1].set_title("Flip-flops (register file dominates)"); ax[1].grid(alpha=0.3); ax[1].set_xticks(Ls)
Ls2 = [1, 2, 4, 8, 16]
ax[2].plot(Ls2, [int(rs[("xc7", l, 16)]["dsp"]) for l in Ls2], "s-", color="#c0392b")
ax[2].set_xlabel("lanes (W = 16)"); ax[2].set_ylabel("DSP48E1 blocks"); ax[2].set_title("DSP use (1 multiplier per lane)"); ax[2].grid(alpha=0.3); ax[2].set_xticks(Ls2)
fig.tight_layout(); fig.savefig(os.path.join(IMG, "resources.png"), dpi=180); plt.close(fig)

# ------------------------------------------------------------ figure 3: Fmax + wall-clock speed-up
fig, ax = plt.subplots(1, 2, figsize=(11, 4.0))
PL = [1, 2, 4]
for dev, lab, c in (("hx8k", "iCE40 HX8K (LUT only)", "#1f77b4"), ("up5k", "iCE40 UP5K (DSP mult.)", "#2ca02c")):
    ax[0].plot(PL, [fm[(dev, l, 16)] for l in PL], "o-", color=c, label=lab)
ax[0].set_xscale("log", base=2); ax[0].set_xticks(PL); ax[0].set_xticklabels(PL)
ax[0].set_ylim(0, 60); ax[0].set_xlabel("lanes (W = 16)"); ax[0].set_ylabel("Fmax (MHz), best of 4 seeds")
ax[0].set_title("Maximum clock frequency"); ax[0].grid(alpha=0.3); ax[0].legend(fontsize=8)
for k in KNAME:
    t = [cyc[(k, l)] / fm[("hx8k", l, 16)] for l in PL]
    ax[1].plot(PL, [t[0] / x for x in t], "o-", color=COL[k], label=KNAME[k])
ax[1].plot(PL, PL, "k--", lw=1, label="ideal (= lanes)")
ax[1].set_xscale("log", base=2); ax[1].set_yscale("log", base=2)
ax[1].set_xticks(PL); ax[1].set_xticklabels(PL); ax[1].set_yticks(PL); ax[1].set_yticklabels(PL)
ax[1].set_xlabel("lanes"); ax[1].set_ylabel("wall-clock speed-up (cycles / Fmax)")
ax[1].set_title("Execution-time speed-up on HX8K"); ax[1].grid(alpha=0.3, which="both"); ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(os.path.join(IMG, "fmax_timespeedup.png"), dpi=180); plt.close(fig)

# ------------------------------------------------------------ markdown tables
L = []
L.append("# Measured results (auto-generated by scripts/make_plots.py - do not edit by hand)\n")
L.append("## 1. Cycle counts, scalar (1 lane) vs SIMD (N = %d elements, W = 16)\n" % N)
L.append("| Kernel | Lanes | Cycles | Cycles/element | Lane-ops/cycle | Speed-up | Efficiency |")
L.append("|---|---:|---:|---:|---:|---:|---:|")
for k in KNAME:
    for l in LANES:
        L.append("| %s | %d | %d | %.2f | %.3f | %.2fx | %.0f %% |" % (KNAME[k], l, cyc[(k, l)], cyc[(k, l)] / N,
                 lops[(k, l)] / cyc[(k, l)], speedup(k, l), 100 * speedup(k, l) / l))
L.append("\nSpeed-up = cycles(1 lane) / cycles(L lanes); efficiency = speed-up / L. The gap to ideal is the 2-cycle pipeline fill and (kernel 0) the one SSET instruction.\n")
L.append("## 2. FPGA resource utilisation of the SIMD core (simd_vpu, W = 16 unless noted)\n")
L.append("| Target | Lanes | W | LUTs | FFs | Carry | DSP |")
L.append("|---|---:|---:|---:|---:|---:|---:|")
names = {"ice40": "iCE40 (Yosys, LUT mult.)", "ice40dsp": "iCE40 + DSP (Yosys)", "xc7": "Xilinx 7-series est. (Yosys)"}
for r in res:
    L.append("| %s | %s | %s | %s | %s | %s | %s |" % (names[r["flow"]], r["lanes"], r["w"], r["lut"], r["ff"], r["carry"], r["dsp"]))
L.append("\nHX8K has 7680 LUT4: the 8-lane LUT-multiplier build (%s LUTs) does not fit. UP5K has 5280 LUT4 and 8 DSP.\n" % rs[("ice40", 8, 16)]["lut"])
L.append("## 3. Maximum frequency (nextpnr, best of 4 seeds, wrapper bench_top, target 100 MHz)\n")
L.append("| Device | Lanes | W | Fmax best (MHz) | Fmax median (MHz) |")
L.append("|---|---:|---:|---:|---:|")
for r in fmax:
    L.append("| %s | %s | %s | %s | %s |" % (r["device"], r["lanes"], r["w"], r["fmax_best"], r["fmax_median"]))
L.append("\n## 4. Wall-clock comparison on iCE40 HX8K (cycles / Fmax, W = 16)\n")
L.append("| Kernel | Lanes | Cycles | Fmax (MHz) | Time (us) | Elements/us | Time speed-up |")
L.append("|---|---:|---:|---:|---:|---:|---:|")
for k in KNAME:
    t1 = cyc[(k, 1)] / fm[("hx8k", 1, 16)]
    for l in PL:
        t = cyc[(k, l)] / fm[("hx8k", l, 16)]
        L.append("| %s | %d | %d | %.2f | %.2f | %.1f | %.2fx |" % (KNAME[k], l, cyc[(k, l)], fm[("hx8k", l, 16)], t, N / t, t1 / t))
L.append("\n## 5. Effect of the pipeline optimisation (iCE40 HX8K, 4 seeds)\n")
L.append("| RTL version | Lanes | Fmax best (MHz) | Fmax median (MHz) | All seeds |")
L.append("|---|---:|---:|---:|---|")
for r in cmp_:
    L.append("| %s | %s | %s | %s | %s |" % (r["version"], r["lanes"], r["fmax_best"], r["fmax_median"], r["fmax_all"]))
L.append("\nv1 = decode and bypass-compare inside the execute stage; v2 (final) = decode registered in stage F and bypass flags pre-computed one cycle early.\n")
open(os.path.join(RESULTS, "RESULTS.md"), "w").write("\n".join(L) + "\n")
print("wrote figures and results/RESULTS.md")
