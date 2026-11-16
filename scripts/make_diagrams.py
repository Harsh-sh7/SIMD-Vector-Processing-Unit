#!/usr/bin/env python3
"""Draw the block diagram and pipeline diagram used in the README / report (matplotlib only)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from common import ROOT

OUT = os.path.join(ROOT, "docs", "img")
os.makedirs(OUT, exist_ok=True)

C_CTRL, C_REG, C_ALU, C_MUX, C_IO, C_PIPE = "#f4d8a8", "#bcd9f2", "#c9e8c4", "#e6d4f0", "#eeeeee", "#fbe3e3"


def box(ax, x, y, w, h, text, fc, fs=8, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=fc, ec="#333333", lw=1.1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal")


def arrow(ax, p, q, text=None, tx=0, ty=0.12, style="-|>", lw=1.2, color="#222222"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=9, lw=lw, color=color))
    if text:
        ax.text((p[0] + q[0]) / 2 + tx, (p[1] + q[1]) / 2 + ty, text, ha="center", fontsize=6.5, color="#444444")


def poly(ax, pts, text=None, tpos=None, color="#222222", lw=1.2, ls="-"):
    xs, ys = zip(*pts)
    ax.plot(xs[:-1] + (xs[-1],), ys[:-1] + (ys[-1],), color=color, lw=lw, ls=ls, solid_capstyle="butt")
    ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>", mutation_scale=9, lw=lw, color=color))
    if text:
        ax.text(tpos[0], tpos[1], text, ha="center", fontsize=6.8, color=color)


def block_diagram():
    fig, ax = plt.subplots(figsize=(12, 6.8))
    ax.set_xlim(0, 25); ax.set_ylim(0.4, 13.4); ax.axis("off")
    ax.text(12.5, 13.0, "SIMD Vector Processing Unit (simd_vpu), shown for LANES = 4, W = 16", ha="center", fontsize=12, fontweight="bold")

    # external inputs
    box(ax, 0.2, 10.0, 2.6, 1.1, "instr[31:0]\ninstr_valid", C_IO)
    box(ax, 0.2, 8.6, 2.6, 1.1, "ld_data\n[LANES*W-1:0]", C_IO)
    box(ax, 0.2, 3.4, 2.6, 1.1, "scalar_in\nscalar_we", C_IO)

    # control unit (wide, three lines)
    box(ax, 3.6, 10.3, 7.4, 2.0, "vec_ctrl  (vector control unit)\nstage-F decode -> registered controls\nhazard unit -> bypass flags\nperformance counters", C_CTRL, 7.3, True)
    box(ax, 3.6, 8.6, 2.4, 1.1, "ld_q\n(load capture)", C_PIPE)
    box(ax, 7.6, 5.0, 3.4, 2.8, "vreg_file\n8 x (LANES*W) bits\n2 read ports\n1 write port\n+ bypass muxes", C_REG, 8, True)
    box(ax, 3.6, 5.6, 2.8, 1.5, "st_valid / st_data\n(VST)\nscalar_out (VEXT)", C_IO, 6.8)
    box(ax, 7.6, 3.4, 2.4, 1.1, "sreg\n(scalar register)", C_REG)

    # lane container
    ax.add_patch(FancyBboxPatch((12.4, 3.2), 5.5, 9.2, boxstyle="round,pad=0.02,rounding_size=0.1", fc="#f3faf1", ec="#2f6b2f", lw=1.5, ls="--"))
    ax.text(15.15, 3.45, "LANES x parallel simd_lane", ha="center", fontsize=7.5, style="italic", color="#2f6b2f")
    for i in range(4):
        y = 10.45 - i * 2.15
        box(ax, 12.7, y, 4.9, 1.75, "", C_ALU)
        ax.text(12.8, y + 1.42, "Lane %d" % i, fontsize=7.5, fontweight="bold")
        box(ax, 12.9, y + 0.12, 1.3, 1.0, "B-mux\nvec/scalar", C_MUX, 6.4)
        box(ax, 14.5, y + 0.12, 1.3, 1.0, "lane_alu\n16 ops", C_ALU, 6.8, True)
        box(ax, 16.1, y + 0.12, 1.3, 1.0, "result\nmux", C_MUX, 6.4)

    # combiner, write-back, outputs
    box(ax, 19.0, 6.2, 2.8, 2.6, "result_combiner\npack lane results\nmask / any / all", C_CTRL, 7.4, True)
    box(ax, 19.0, 1.0, 2.8, 1.5, "wb regs\n(wb_we, wb_vd,\nwb_data)", C_PIPE, 7.2)
    box(ax, 22.4, 6.9, 2.4, 1.2, "vmask / vany\nvall / flags_valid", C_IO, 7)

    # arrows
    poly(ax, [(2.8, 10.55), (3.6, 10.55)])
    poly(ax, [(2.8, 9.15), (3.6, 9.15)])
    poly(ax, [(2.8, 3.95), (7.6, 3.95)])
    poly(ax, [(11.0, 10.6), (12.4, 10.6)], "controls", (11.7, 10.85))
    poly(ax, [(4.8, 10.3), (4.8, 9.7)], color="#888888")
    poly(ax, [(6.0, 9.15), (12.4, 9.15)], "load data (one slice per lane)", (9.2, 9.35))
    poly(ax, [(10.0, 3.95), (12.4, 3.95)], "scalar", (11.2, 4.15))
    poly(ax, [(11.0, 6.9), (12.4, 6.9)], "rd1 / rd2", (11.7, 7.15), color="#1b4f8a")
    poly(ax, [(7.6, 6.35), (6.4, 6.35)], color="#888888")
    poly(ax, [(17.9, 7.5), (19.0, 7.5)])
    poly(ax, [(21.8, 7.5), (22.4, 7.5)])
    poly(ax, [(20.4, 6.2), (20.4, 2.5)])
    poly(ax, [(19.0, 1.75), (11.5, 1.75), (11.5, 5.5), (11.0, 5.5)], "write-back + bypass (no stalls)", (15.2, 1.35), color="#aa3333", ls="--")
    fig.savefig(os.path.join(OUT, "block_diagram.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def pipeline_diagram():
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.set_xlim(0, 20); ax.set_ylim(0, 6.5); ax.axis("off")
    ax.text(10, 6.1, "3-stage pipeline: one vector instruction issued per cycle, no stalls", ha="center", fontsize=11, fontweight="bold")
    stages = [("F\nfetch / decode\nhazard check", C_CTRL), ("E\nreg read + bypass\nLANES x ALU\nresult combine", C_ALU), ("W\nregister write-back\nstore / flag / scalar out", C_REG)]
    for i, (t, c) in enumerate(stages):
        box(ax, 0.8 + i * 6.3, 3.2, 5.4, 2.0, t, c, 9, True)
        if i < 2:
            arrow(ax, (6.2 + i * 6.3, 4.2), (7.1 + i * 6.3, 4.2))
    labels = ["I0", "I1", "I2", "I3"]
    cols = ["#e8f0ff", "#fff0d6", "#e3f6e3", "#f6e3f6"]
    for r, lab in enumerate(labels):
        for s in range(3):
            xx = 0.8 + (s + r) * 1.6 * 1.0
            ax.add_patch(FancyBboxPatch((xx, 2.2 - r * 0.55), 1.5, 0.45, boxstyle="round,pad=0.01", fc=cols[r], ec="#444444", lw=0.8))
            ax.text(xx + 0.75, 2.42 - r * 0.55, "%s:%s" % (lab, "FEW"[s]), ha="center", va="center", fontsize=7)
    for c in range(6):
        ax.text(0.8 + c * 1.6 + 0.75, 2.55 + 0.35, "t%d" % c, ha="center", fontsize=6.5, color="#666666")
    ax.text(12.5, 1.35, "Fully pipelined: a dependent instruction may issue the very next\ncycle - the hazard unit pre-computes the bypass flag in stage F.\nPipeline fill latency = 2 cycles.", fontsize=8, va="center")
    fig.savefig(os.path.join(OUT, "pipeline.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    block_diagram(); pipeline_diagram(); print("wrote", OUT)
