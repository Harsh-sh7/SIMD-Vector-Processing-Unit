#!/usr/bin/env python3
"""
Run a short demo (4 lanes, 8 elements, mixed kernel), dump a VCD, and draw a waveform figure showing
all four lanes executing the same instruction in the same cycle. The raw VCD (results/perf_demo.vcd)
can also be opened in GTKWave / Surfer / WaveTrace for the video.
"""
import os, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import *

LANES, W = 4, 16
OPN = ["ADD", "SUB", "AND", "OR", "XOR", "SLL", "SRL", "SRA", "MUL", "EQ", "NE", "LT", "GT", "LTU", "MIN", "MAX"]


def parse_vcd(path):
    ids, sig, scope = {}, {}, []
    with open(path) as f:
        lines = iter(f)
        for ln in lines:
            t = ln.split()
            if not t:
                continue
            if t[0] == "$scope": scope.append(t[2])
            elif t[0] == "$upscope": scope.pop()
            elif t[0] == "$var":
                name = ".".join(scope + [t[4]])
                ids.setdefault(t[3], []).append(name)
                sig[name] = []
            elif t[0] == "$enddefinitions":
                break
        now = 0
        for ln in lines:
            ln = ln.strip()
            if not ln: continue
            if ln[0] == "#": now = int(ln[1:]); continue
            if ln[0] == "b":
                v, i = ln[1:].split()
            else:
                v, i = ln[0], ln[1:]
            for n in ids.get(i, []):
                sig[n].append((now, v))
    return sig


def val_at(ch, t):
    cur = "x"
    for tt, v in ch:
        if tt <= t: cur = v
        else: break
    return cur


def toint(v):
    return int(v, 2) if set(v) <= set("01") and v else None


def main():
    ok, out = iverilog_run(os.path.join(TB, "tb_perf.v"), {"LANES": LANES, "N": 8, "KERNEL": 0}, "wave", plusargs=["+vcd"])
    assert ok and "RESULT CORRECT" in out, out
    sig = parse_vcd(os.path.join(RESULTS, "perf_demo.vcd"))
    P = "tb_perf."
    # sample each cycle just before its rising edge (clock rises at 5, 15, 25 ... ns -> ps timescale 1000)
    t0 = 3
    cycles = []
    c = 3                                       # first cycle after reset deasserts, approx
    # locate first valid instruction
    first = None
    for t, v in sig[P + "instr_valid"]:
        if v == "1": first = t; break
    start = (first // 10000) * 10000 + 5000     # align to a rising edge
    ncyc = 24
    T = [start + k * 10000 - 500 for k in range(ncyc)]

    def mnemonic_f(t):
        iv = val_at(sig[P + "instr_valid"], t)
        ins = toint(val_at(sig[P + "instr"], t))
        if iv != "1" or ins is None: return ""
        cls = (ins >> 29) & 7; op = (ins >> 25) & 15; vd = (ins >> 22) & 7; s1 = (ins >> 19) & 7; s2 = (ins >> 16) & 7
        return {0: "NOP", 1: "V%s v%d,v%d,v%d" % (OPN[op], vd, s1, s2), 2: "V%s.S v%d,v%d,s" % (OPN[op], vd, s1),
                3: "VLD v%d" % vd, 4: "VST v%d" % s1, 5: "VSPLAT v%d" % vd, 6: "SSET", 7: "VEXT"}[cls]

    def mnemonic_e(t):
        g = lambda n: toint(val_at(sig[P + "dut.u_ctrl." + n], t))
        if g("alu_en") == 1:
            return "V%s%s v%d" % (OPN[g("op")], ".S" if g("use_sc") else "", g("vd"))
        if g("res_sel") == 1 and g("reg_we") == 1: return "VLD v%d" % g("vd")
        if g("st_en") == 1: return "VST v%d" % g("vs1")
        if g("sset_en") == 1: return "SSET"
        return ""

    rows = [("clk", None)]
    fig, ax = plt.subplots(figsize=(14, 6.2))
    labels, y = [], 0
    def draw_bus(y, texts, color):
        prev = None
        for k, tx in enumerate(texts):
            if tx:
                ax.add_patch(plt.Rectangle((k + 0.04, y + 0.12), 0.92, 0.76, fc=color, ec="#444", lw=0.8))
                ax.text(k + 0.5, y + 0.5, tx.replace(" ", "\n", 1) if len(tx) > 9 else tx, ha="center", va="center", fontsize=6.0)
    # rows top -> bottom
    spec = [
        ("F: instruction in", [mnemonic_f(t) for t in T], "#f4d8a8"),
        ("E: executing", [mnemonic_e(t) for t in T], "#c9e8c4"),
    ]
    wb_vd = [(toint(val_at(sig[P + "dut.wb_we"], t)), toint(val_at(sig[P + "dut.wb_vd"], t))) for t in T]
    spec.append(("W: write-back reg", ["v%d <=" % vd if we == 1 else "" for we, vd in wb_vd], "#bcd9f2"))
    wbd = [val_at(sig[P + "dut.wb_data"], t) for t in T]
    for l in range(LANES):
        tx = []
        for (we, _), d in zip(wb_vd, wbd):
            n = toint(d)
            tx.append("%04x" % ((n >> (l * W)) & 0xFFFF) if (we == 1 and n is not None) else "")
        spec.append(("lane %d result" % l, tx, "#e6d4f0"))
    stv = [toint(val_at(sig[P + "st_valid"], t)) for t in T]
    std = [toint(val_at(sig[P + "st_data"], t)) for t in T]
    for l in range(LANES):
        spec.append(("store lane %d" % l, ["%04x" % ((d >> (l * W)) & 0xFFFF) if v == 1 else "" for v, d in zip(stv, std)], "#fbe3e3"))
    n = len(spec)
    for r, (name, texts, col) in enumerate(spec):
        yy = n - 1 - r
        draw_bus(yy, texts, col)
        labels.append((yy + 0.5, name))
    ax.set_yticks([a for a, _ in labels]); ax.set_yticklabels([b for _, b in labels], fontsize=8)
    ax.set_xticks([k + 0.5 for k in range(ncyc)]); ax.set_xticklabels([str(k) for k in range(ncyc)], fontsize=7)
    ax.set_xlim(0, ncyc); ax.set_ylim(0, n)
    ax.set_xlabel("clock cycle (relative to first instruction)")
    ax.set_title("Waveform (from simulation VCD): 4 lanes execute every vector instruction in the SAME cycle - mixed kernel, 8 elements = 2 chunks", fontsize=9)
    ax.grid(axis="x", alpha=0.25)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "docs", "img", "waveform.png"), dpi=170)
    print("wrote docs/img/waveform.png")


if __name__ == "__main__":
    main()
