#!/usr/bin/env python3
"""
Before/after optimisation study: Fmax of the first RTL version (decode + bypass-compare inside the
execute stage, snapshot in results/v1_rtl_snapshot) versus the final RTL (decode registered in stage F,
bypass flags pre-computed one cycle early). iCE40 HX8K, same 4 placer seeds, LANES=4 W=16.
"""
import csv, os, re, concurrent.futures as cf
from common import *

SEEDS = [1, 2, 3, 4]
V1 = os.path.join(RESULTS, "v1_rtl_snapshot")


def build(tag, rtl_dir, lanes):
    js = os.path.join(BUILD, "cmp_%s_L%d.json" % (tag, lanes))
    script = ("read_verilog -I %s %s %s; chparam -set LANES %d -set W 16 bench_top; synth_ice40 -top bench_top -json %s"
              % (rtl_dir, " ".join(rtl_files(rtl_dir)), os.path.join(SYNTH, "bench_top.v"), lanes, js))
    run(["yosys", "-q", "-p", script], log=os.path.join(LOGS, "cmp_%s_L%d_yosys.log" % (tag, lanes)), check=True)
    return js


def pnr(js, seed, tag, lanes):
    rc, out = run(["nextpnr-ice40", "--hx8k", "--package", "ct256", "--json", js, "--freq", "100", "--seed", str(seed)],
                  log=os.path.join(LOGS, "cmp_%s_L%d_seed%d.log" % (tag, lanes, seed)))
    fm = re.findall(r"Max frequency for clock '[^']*': ([0-9.]+) MHz", out)
    return float(fm[-1])


def main():
    rows = []
    for lanes in (1, 4):
        for tag, d in (("v1", V1), ("v2", RTL)):
            js = build(tag, d, lanes)
            with cf.ThreadPoolExecutor(max_workers=4) as ex:
                vals = sorted(ex.map(lambda s: pnr(js, s, tag, lanes), SEEDS))
            rows.append(dict(version=tag, lanes=lanes, fmax_best=max(vals), fmax_median=vals[len(vals) // 2], fmax_all=" ".join("%.2f" % v for v in vals)))
            print(rows[-1], flush=True)
    with open(os.path.join(RESULTS, "fmax_v1_vs_v2.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader(); wr.writerows(rows)


if __name__ == "__main__":
    main()
