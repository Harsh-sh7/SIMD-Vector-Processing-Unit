#!/usr/bin/env python3
"""
FPGA resource utilisation and maximum-frequency sweep (open-source flow: Yosys + nextpnr).

 * Resources are measured on the SIMD core ALONE (simd_vpu), not the timing wrapper.
     - iCE40 (LUT4 + carry, multipliers built from LUTs)         : synth_ice40
     - iCE40 with hard DSP multipliers (SB_MAC16, UP5K style)     : synth_ice40 -dsp
     - Xilinx 7-series estimate (LUT6 / CARRY4 / DSP48E1)         : synth_xilinx -family xc7
 * Fmax is measured by placing and routing synth/bench_top.v (core + I/O-folding wrapper)
   with nextpnr, best of several placer seeds:
     - iCE40 HX8K  (LUT-only)       - iCE40 UP5K (with DSP multipliers)
 Results -> results/synth.csv, logs -> results/logs/synth_*/
"""
import csv, os, re, sys, concurrent.futures as cf
from common import *

SEEDS = [1, 2, 3, 4]
TARGET_MHZ = 100
LIMITS = {"hx8k": 7680, "up5k": 5280}        # LUT4 capacity

CORE_CONFIGS = [(1, 16), (2, 16), (4, 16), (8, 16), (4, 8), (4, 32)]
XC7_EXTRA = [(16, 16)]
PNR_CONFIGS = [(1, 16), (2, 16), (4, 16), (4, 8)]


def yosys_core(lanes, w, flow):
    tag = "%s_L%d_W%d" % (flow, lanes, w)
    logdir = os.path.join(LOGS, "synth_core")
    os.makedirs(logdir, exist_ok=True)
    stat = os.path.join(logdir, tag + ".stat")
    synth = {"ice40": "synth_ice40 -top simd_vpu",
             "ice40dsp": "synth_ice40 -dsp -top simd_vpu",
             "xc7": "synth_xilinx -family xc7 -flatten -top simd_vpu"}[flow]
    script = ("read_verilog -I %s %s; chparam -set LANES %d -set W %d simd_vpu; %s; tee -o %s stat"
              % (RTL, " ".join(rtl_files()), lanes, w, synth, stat))
    rc, out = run(["yosys", "-p", script], log=os.path.join(logdir, tag + ".log"))
    if rc != 0:
        sys.exit("yosys failed for " + tag)
    cells = {}
    for line in open(stat):
        m = re.match(r"\s+(\d+)\s+(\$?[A-Za-z_0-9]+)\s*$", line)
        if m:
            cells[m.group(2)] = int(m.group(1))
    return cells


def summarize(flow, cells):
    if flow.startswith("ice40"):
        luts = cells.get("SB_LUT4", 0)
        ffs = sum(v for k, v in cells.items() if k.startswith("SB_DFF"))
        return dict(lut=luts, ff=ffs, carry=cells.get("SB_CARRY", 0),
                    dsp=cells.get("SB_MAC16", 0), bram=cells.get("SB_RAM40_4K", 0))
    luts = sum(v for k, v in cells.items() if re.fullmatch(r"LUT[1-6]", k))
    ffs = sum(v for k, v in cells.items() if re.fullmatch(r"FD[A-Z]*E?", k))
    return dict(lut=luts, ff=ffs, carry=cells.get("CARRY4", 0),
                dsp=cells.get("DSP48E1", 0), bram=0,
                muxf=cells.get("MUXF7", 0) + cells.get("MUXF8", 0))


def pnr_one(args):
    lanes, w, dev, seed = args
    dsp = (dev == "up5k")
    tag = "%s_L%d_W%d" % (dev, lanes, w)
    d = os.path.join(LOGS, "synth_pnr")
    os.makedirs(d, exist_ok=True)
    js = os.path.join(BUILD, "%s.json" % tag)
    if seed == SEEDS[0]:
        synth = "synth_ice40 %s-top bench_top -json %s" % ("-dsp " if dsp else "", js)
        script = ("read_verilog -I %s %s %s; chparam -set LANES %d -set W %d bench_top; %s"
                  % (RTL, " ".join(rtl_files()), os.path.join(SYNTH, "bench_top.v"), lanes, w, synth))
        rc, _ = run(["yosys", "-q", "-p", script], log=os.path.join(d, tag + "_yosys.log"))
        if rc != 0:
            sys.exit("yosys failed for " + tag)
    return lanes, w, dev, seed


def pnr_run(lanes, w, dev, seed):
    tag = "%s_L%d_W%d" % (dev, lanes, w)
    js = os.path.join(BUILD, "%s.json" % tag)
    pkg = {"hx8k": "ct256", "up5k": "sg48"}[dev]
    log = os.path.join(LOGS, "synth_pnr", "%s_seed%d.log" % (tag, seed))
    rc, out = run(["nextpnr-ice40", "--%s" % dev, "--package", pkg, "--json", js,
                   "--freq", str(TARGET_MHZ), "--seed", str(seed)], log=log)
    fm = re.findall(r"Max frequency for clock '[^']*': ([0-9.]+) MHz", out)
    return float(fm[-1]) if fm else None


def main():
    rows = []
    # ---------------- core resources ----------------
    for flow in ("ice40", "ice40dsp", "xc7"):
        cfgs = CORE_CONFIGS + (XC7_EXTRA if flow == "xc7" else [])
        for lanes, w in cfgs:
            r = summarize(flow, yosys_core(lanes, w, flow))
            r.update(flow=flow, lanes=lanes, w=w)
            rows.append(r)
            print("%-9s L=%-2d W=%-2d  %s" % (flow, lanes, w, r))
    with open(os.path.join(RESULTS, "synth_resources.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["flow", "lanes", "w", "lut", "ff", "carry", "dsp", "bram", "muxf"])
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in wr.fieldnames})

    # ---------------- place & route / Fmax ----------------
    jobs, res_lut = [], {}
    for r in rows:
        res_lut[(r["flow"], r["lanes"], r["w"])] = r["lut"]
    fmax_rows = []
    for dev, flow in (("hx8k", "ice40"), ("up5k", "ice40dsp")):
        for lanes, w in PNR_CONFIGS:
            lut = res_lut[(flow, lanes, w)]
            if lut > LIMITS[dev] * 0.97:
                fmax_rows.append(dict(device=dev, lanes=lanes, w=w, fmax_best="", fmax_median="", seeds="", note="does not fit"))
                continue
            pnr_one((lanes, w, dev, SEEDS[0]))              # synthesise wrapper once
            jobs.append((lanes, w, dev))
    with cf.ThreadPoolExecutor(max_workers=min(6, os.cpu_count() or 2)) as ex:
        futs = {}
        for (lanes, w, dev) in jobs:
            for s in SEEDS:
                futs[ex.submit(pnr_run, lanes, w, dev, s)] = (lanes, w, dev, s)
        got = {}
        for fu in cf.as_completed(futs):
            k = futs[fu]
            got.setdefault(k[:3], []).append(fu.result())
            print("PnR done", k, fu.result(), flush=True)
    for (lanes, w, dev), vals in sorted(got.items()):
        vals = sorted(v for v in vals if v)
        fmax_rows.append(dict(device=dev, lanes=lanes, w=w, fmax_best=max(vals),
                              fmax_median=vals[len(vals) // 2], seeds=len(vals), note=""))
    with open(os.path.join(RESULTS, "synth_fmax.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["device", "lanes", "w", "fmax_best", "fmax_median", "seeds", "note"])
        wr.writeheader()
        for r in sorted(fmax_rows, key=lambda r: (r["device"], r["w"], r["lanes"])):
            wr.writerow(r)
            print(r)


if __name__ == "__main__":
    main()
