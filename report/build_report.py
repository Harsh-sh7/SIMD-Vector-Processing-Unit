#!/usr/bin/env python3
"""Builds report/SIMD_VPU_IEEE_Report.docx (IEEE two-column style) from measured results.
Text in [[double brackets]] is rendered with yellow highlight = something the team must fill in."""
import csv, os, re
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "docs", "img")
RES = os.path.join(ROOT, "results")


def rd(n):
    return list(csv.DictReader(open(os.path.join(RES, n))))


perf = {(int(r["kernel"]), int(r["lanes"])): int(r["cycles"]) for r in rd("perf_cycles.csv")}
fmax = {(r["device"], int(r["lanes"]), int(r["w"])): float(r["fmax_best"]) for r in rd("synth_fmax.csv") if r["fmax_best"]}
rs = {(r["flow"], int(r["lanes"]), int(r["w"])): r for r in rd("synth_resources.csv")}
cmpv = {(r["version"], int(r["lanes"])): r for r in rd("fmax_v1_vs_v2.csv")}
sp = lambda k, l: perf[(k, 1)] / perf[(k, l)]

doc = Document()
FONT = "Times New Roman"
st = doc.styles["Normal"]
st.font.name = FONT; st.font.size = Pt(10)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.left_margin = sec.right_margin = Inches(0.7)
sec.top_margin, sec.bottom_margin = Inches(0.75), Inches(0.9)


def set_cols(section, num, space=360):
    sp_ = section._sectPr
    c = sp_.find(qn("w:cols"))
    if c is None:
        c = OxmlElement("w:cols"); sp_.append(c)
    c.set(qn("w:num"), str(num)); c.set(qn("w:space"), str(space))


def runs(p, text, size=10, bold=False, italic=False):
    """Add text; [[x]] segments get yellow highlight; **x** bold; _x_ not supported (keep simple)."""
    for part in re.split(r"(\[\[.*?\]\]|\*\*.*?\*\*)", text):
        if not part:
            continue
        if part.startswith("[["):
            r = p.add_run("[" + part[2:-2] + "]"); r.font.highlight_color = WD_COLOR_INDEX.YELLOW
            r.bold = bold
        elif part.startswith("**"):
            r = p.add_run(part[2:-2]); r.bold = True
        else:
            r = p.add_run(part); r.bold = bold
        r.italic = italic; r.font.size = Pt(size); r.font.name = FONT


def para(text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=10, bold=False, italic=False, indent=True, after=4, before=0, keep=False):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_after, pf.space_before = Pt(after), Pt(before)
    pf.line_spacing = 1.0
    if indent: pf.first_line_indent = Inches(0.17)
    if keep: pf.keep_with_next = True
    runs(p, text, size, bold, italic)
    return p


def h1(t):
    p = para(t.upper(), WD_ALIGN_PARAGRAPH.CENTER, 10, False, False, False, after=3, before=8, keep=True)
    for r in p.runs: r.font.small_caps = False


def h2(t):
    para(t, WD_ALIGN_PARAGRAPH.LEFT, 10, False, True, False, after=2, before=4, keep=True)


def caption(t, size=8):
    return para(t, WD_ALIGN_PARAGRAPH.CENTER, size, False, False, False, after=6, before=2)


def figure(name, width, cap):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0); p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(os.path.join(IMG, name), width=Inches(width))
    caption(cap)


def wide_begin():
    s = doc.add_section(WD_SECTION.CONTINUOUS); set_cols(s, 1)


def wide_end():
    s = doc.add_section(WD_SECTION.CONTINUOUS); set_cols(s, 2)


def table(rows, widths, cap, header=True, size=7.5):
    caption(cap, 8).paragraph_format.keep_with_next = True
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            c = t.cell(i, j); c.width = Inches(widths[j])
            c.paragraphs[0].paragraph_format.space_after = Pt(0)
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            runs(c.paragraphs[0], str(cell), size, bold=(header and i == 0))
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# ------------------------------------------------------------------ title block (single column)
set_cols(sec, 1)
para("Design, Verification and FPGA Evaluation of a Parameterised 4-Lane SIMD Vector Processing Unit with a Scalar-Baseline Speed-up Study",
     WD_ALIGN_PARAGRAPH.CENTER, 20, True, False, False, after=6)
para("[[Member 1 name]], [[Member 2 name]], [[Member 3 name]], [[Member 4 name]], [[Member 5 name]]", WD_ALIGN_PARAGRAPH.CENTER, 11, False, False, False, after=1)
para("Master of Computer Applications (MCA), [[University / institute name]], [[City, Country]]", WD_ALIGN_PARAGRAPH.CENTER, 9, False, True, False, after=1)
para("Project 11: SIMD Vector Processing Unit  |  Repository: [[GitHub URL]]", WD_ALIGN_PARAGRAPH.CENTER, 9, False, True, False, after=8)

body = doc.add_section(WD_SECTION.CONTINUOUS); set_cols(body, 2)

# ------------------------------------------------------------------ abstract
a4 = perf[(0, 4)]; a1 = perf[(0, 1)]
para("**Abstract**—Data-level parallelism lets one instruction operate on many data elements at once, "
     "and is the foundation of vector processors, multimedia extensions and GPUs. This paper presents the design, verification and FPGA evaluation of a small, "
     "fully parameterised SIMD vector processing unit written in Verilog. The unit has LANES identical W-bit ALU lanes (default 4 × 16 bit), "
     "an 8-entry vector register file, a vector control unit with a hazard/bypass unit, lane operand and result multiplexers, a result combiner "
     "that produces compare masks, a scalar interface, and hardware performance counters. A 3-stage pipeline issues one 16-operation vector instruction every cycle without stalls. "
     "A scalar baseline is obtained from the same micro-architecture with one lane, so the comparison isolates data-level parallelism. "
     "Verification combines an exhaustive 1,048,576-case lane-ALU test, a self-checking system testbench with functional-coverage closure over eight lane/width configurations, "
     "and mutation testing in which all 21 non-equivalent injected bugs were detected. On a 64-element workload the 4-lane unit needs %d cycles versus %d for the scalar baseline "
     "(%.2f× speed-up, %.0f %% efficiency), and %.2f× in wall-clock time on an iCE40 HX8K at the measured Fmax. "
     "The 4-lane core uses %s LUT4 / %s FF on iCE40 and about %s LUT / %s FF / 4 DSP48E1 on a Xilinx 7-series estimate. "
     "The same architecture was also built as a 4-lane gate-level chip in Digital Logic Sim and [[cross-checked against the RTL with shared test vectors - confirm after doing the DLS check]]."
     % (a4, a1, sp(0, 4), 100 * sp(0, 4) / 4, sp(0, 4) * 0 + (perf[(0, 1)] / fmax[("hx8k", 1, 16)]) / (perf[(0, 4)] / fmax[("hx8k", 4, 16)]),
        rs[("ice40", 4, 16)]["lut"], rs[("ice40", 4, 16)]["ff"], rs[("xc7", 4, 16)]["lut"], rs[("xc7", 4, 16)]["ff"]),
     indent=False, size=9, bold=False, after=3)
para("**Index Terms**—SIMD, vector processor, data-level parallelism, Verilog, FPGA, speed-up, functional verification, mutation testing.",
     indent=False, size=9, italic=True, after=4)

# ------------------------------------------------------------------ I intro
h1("I. Introduction")
para("Many workloads—image filters, signal processing, linear algebra, neural-network inference—apply the same operation to long arrays of independent elements. "
     "Executing them one element at a time wastes the available parallelism. A Single-Instruction-Multiple-Data (SIMD) unit replicates the arithmetic logic unit into several "
     "lanes controlled by one instruction stream, so N elements are processed in the time of one, at the cost of roughly N times the datapath area.")
para("The objective of this project (Project 11, SIMD Vector Processing Unit) is to design a small SIMD unit that performs multiple identical arithmetic and logic operations "
     "in parallel, to implement the same workload on a scalar and on a SIMD version, to verify the vector results, and to measure cycle count, throughput and FPGA resource usage. "
     "Our contributions are: (i) a parameterised Verilog SIMD core with 16 lane operations (add, subtract, logic, shifts, multiply, six comparisons, min, max); "
     "(ii) a hazard-free 3-stage pipeline with pre-computed bypassing; (iii) a rigorous verification environment including exhaustive, constrained-random, coverage and mutation testing; "
     "(iv) quantitative scalar-versus-SIMD results on three kernels and 1–16 lanes; (v) FPGA resource and maximum-frequency results using an open-source flow; and "
     "(vi) an independent 4-lane implementation in Digital Logic Sim, with shared golden test vectors for cross-checking it against the RTL.")

# ------------------------------------------------------------------ II lit
h1("II. Literature Review")
para("Flynn’s taxonomy classifies SIMD as one instruction stream acting on multiple data streams [1]. The earliest commercially successful realisation was the vector supercomputer: "
     "the Cray-1 combined vector registers with pipelined functional units and chaining [2]. Hennessy and Patterson analyse the three modern families of data-level parallelism—vector, "
     "multimedia-SIMD and GPU—and show that vector architectures achieve high performance per instruction fetched because one instruction describes many operations [3].")
para("General-purpose processors adopted short-vector “subword” SIMD: HP’s MAX-2 [4] and Intel’s MMX [5] pack several small elements into one wide register and operate on all of them with one instruction. "
     "The RISC-V “V” extension returns to the vector-length-agnostic model of classic vector machines [6], and GPUs generalise the idea to thousands of lanes grouped into warps [7].")
para("On FPGAs, soft vector processors turn lane count into a scalable design parameter. VESPA reported performance scaling of roughly 1.8× to 6.3× for 2 to 16 lanes on EEMBC benchmarks [8], "
     "and the VIPERS soft vector processor reached up to 44× over a Nios II/s with 32 lanes at up to 26× the area [9]. These systems are full vector processors with memory systems and compilers; "
     "they are too large to study end-to-end in a course project. The open-source Yosys and nextpnr tools [10] now allow reproducible synthesis, resource counting and timing analysis for commercial devices without vendor licences. "
     "Sebastian Lague’s Digital Logic Sim [11] allows computer architecture concepts to be built from gates, which suits a bottom-up demonstration of the lane structure.")
para("**Gap addressed.** Prior work targets large systems. This project provides a small, completely specified, exhaustively verified SIMD unit whose lane count and width are parameters, "
     "with a like-for-like scalar baseline, measured cycle and frequency data, and a gate-level DLS counterpart.")

# ------------------------------------------------------------------ III proposed
h1("III. Proposed Solution")
h2("A. Architecture")
para("The design (Fig. 1) is hierarchical. **simd_vpu** instantiates LANES copies of **simd_lane**, each containing an operand-B multiplexer (vector register lane or broadcast scalar), "
     "a **lane_alu** and a result multiplexer (ALU, load bus or broadcast). **vreg_file** holds eight vector registers of LANES×W bits with two read ports, one write port and bypass multiplexers. "
     "**vec_ctrl** decodes instructions, hosts the hazard unit and the performance counters. **result_combiner** packs the lane outputs and derives a per-lane predicate mask with ANY/ALL reductions. "
     "The optional scalar interface provides an external scalar-register write port, a broadcast operand, and a lane-extract instruction.")
wide_begin()
figure("block_diagram.png", 6.0, "Fig. 1. Block diagram of the SIMD vector processing unit (LANES = 4, W = 16).")
wide_end()
h2("B. Instruction set")
para("A 32-bit instruction holds a 3-bit class, a 4-bit operation, three 3-bit register fields and a 16-bit immediate. Classes are VV (vd = vs1 op vs2), VS (vs2 replaced by the broadcast scalar), "
     "VLD, VST, VSPLAT, SSET (scalar immediate) and VEXT (extract a lane). Table I lists the 16 lane operations. Compare operations return all-ones or zero per lane, "
     "so their result can be used directly as an AND mask for branch-free selection.")
table([["Code", "Op", "Code", "Op", "Code", "Op", "Code", "Op"],
       ["0", "ADD", "4", "XOR", "8", "MUL", "C", "GT (s)"],
       ["1", "SUB", "5", "SLL", "9", "EQ", "D", "LTU"],
       ["2", "AND", "6", "SRL", "A", "NE", "E", "MIN (s)"],
       ["3", "OR", "7", "SRA", "B", "LT (s)", "F", "MAX (s)"]],
      [0.4, 0.45, 0.4, 0.45, 0.4, 0.5, 0.4, 0.55], "TABLE I.  LANE OPERATIONS (s = signed)")
h2("C. Pipeline and hazard handling")
para("The three stages are F (decode and hazard check, results registered), E (register read with bypass, lane multiplexers, LANES×ALU, result combine) and W (write-back, store/flag/scalar outputs). "
     "One instruction is accepted per cycle. Because E results are written back in W, a dependent instruction one cycle behind would read stale data; the hazard unit therefore compares "
     "the source fields of the instruction in F with the destination of the instruction in E and registers a bypass flag, so the bypass multiplexer select comes straight from a flip-flop. "
     "No stalls are ever needed, and the pipeline fill latency is two cycles. This pre-computation was a deliberate optimisation of the first RTL version, in which decode and comparison sat in the execute stage (Section V-D).")
h2("D. Scalar baseline")
para("The scalar baseline is the same RTL, ISA and program with LANES = 1 (module scalar_baseline). Because pipeline, instruction set, clocking and mapping are identical, "
     "any difference in cycles is caused only by data-level parallelism. The SIMD program is the scalar program with each vector instruction covering LANES elements; "
     "the load/store bus is LANES×W wide in the SIMD build, i.e. memory bandwidth scales with the lane count (an ideal-memory assumption discussed in Section VI).")
h2("E. Digital Logic Sim implementation")
para("In addition to the Verilog RTL, a 4-lane SIMD chip (SIMD_4LANE) was built from primitive gates in Sebastian Lague’s Digital Logic Sim [11]. It uses [[lane width, e.g. 8]]-bit lanes, "
     "[[describe: ALU sub-chip, operations supported, register/latch storage, opcode encoding]]. [[Insert DLS screenshot of the top-level chip as Fig. X]]. "
     "To prove functional equivalence, a Python reference model generates golden vectors (op, A, B, expected) that are replayed against the RTL in simulation (192 vectors per width, zero mismatches) "
     "and keyed into the DLS chip by hand: [[state result, e.g. all N sampled vectors matched]].")

# ------------------------------------------------------------------ IV verification
h1("IV. Verification")
para("**Exhaustive lane-ALU test.** For W = 8 all 16 operations were checked for all 65,536 operand pairs (1,048,576 checks, 0 errors) against an independent 64-bit integer reference model.")
para("**System testbench.** A self-checking testbench keeps an architectural model (registers and scalar register) updated in program order and queues the expected store, extract and predicate outputs. "
     "It runs (1) a directed sweep of all operations in VV and VS form with corner operands (0, 1, −1, minimum, maximum, alternating bits), (2) directed hazard tests (RAW at distance 1, 2, 3, WAW, "
     "self-dependency), (3) 20,000 constrained-random instructions biased towards register collisions, with random bubbles, NOPs with junk fields and external scalar writes. "
     "The register file is compared with the model after every drain. Functional-coverage bins (every operation × VV/VS, every class, every lane producing non-zero data, operand corner classes, hazard types, "
     "compare predicate all-true/mixed/all-false) must all be hit or the test fails. The regression passes for (LANES, W) = (1,16), (2,16), (4,16), (8,16), (4,8), (4,32), (8,8), (16,16), "
     "each with about 21,000 instructions.")
para("**Mutation testing.** To show the testbench can fail, 21 deliberate bugs (e.g. SRA as logical shift, signed compare as unsigned, removed bypass, wrong hazard comparison, VEXT stuck on lane 0, ignored instr_valid) "
     "were injected one at a time; all 21 were detected (100 %). One additional change (removing the load-capture clock enable) is functionally equivalent and correctly survives.")

# ------------------------------------------------------------------ V results
h1("V. Results")
h2("A. Method")
para("Three kernels run on 64 elements (W = 16): a mixed kernel y = max((a+b)·3 − (a≪3), a) (8 instructions per chunk, 5 ALU); vector add (4 per chunk); and a branch-free minimum "
     "using the compare mask, y = b ⊕ ((a ⊕ b) & mask) (7 per chunk). Every output is verified against a golden model. Cycles are counted from the first issued instruction until the last result is visible. "
     "Resources come from Yosys for the SIMD core only; Fmax comes from nextpnr (best of four seeds, 100 MHz target) on a wrapper that serialises I/O so that the reported critical path is internal. "
     "All tools are open-source: Icarus Verilog 13, Yosys 0.71, nextpnr-ice40.")
h2("B. Cycle count and speed-up")
rows = [["Lanes", "Cycles", "Speed-up", "Effic.", "Lane-ops/cyc"]]
for l in (1, 2, 4, 8, 16):
    rows.append([l, perf[(0, l)], "%.2f×" % sp(0, l), "%.0f %%" % (100 * sp(0, l) / l), "%.2f" % (320.0 / perf[(0, l)])])
table(rows, [0.5, 0.6, 0.7, 0.55, 0.9], "TABLE II.  MIXED KERNEL, 64 ELEMENTS, SCALAR (1 LANE) VS SIMD")
para("Table II shows near-linear scaling: %.2f× with four lanes (ideal 4×). The residual loss is the fixed two-cycle pipeline fill and one scalar-setup instruction, "
     "which matter more as the cycle count shrinks (efficiency falls to %.0f %% at 16 lanes). Vector add and min-select give %.2f× and %.2f× at four lanes, "
     "so speed-up is nearly independent of the ALU-to-memory instruction ratio under the ideal-memory assumption (Fig. 2)."
     % (sp(0, 4), 100 * sp(0, 16) / 16, sp(1, 4), sp(2, 4)))
wide_begin()
figure("speedup.png", 6.2, "Fig. 2. Cycle count and cycle speed-up versus lanes for the three kernels (log–log).")
wide_end()
h2("C. FPGA resource utilisation")
rows = [["Target", "Lanes", "LUT", "FF", "DSP"]]
for flow, nm in (("ice40", "iCE40 LUT-mult."), ("xc7", "Xilinx-7 est.")):
    for l in (1, 4, 8):
        r = rs[(flow, l, 16)]
        rows.append([nm, l, r["lut"], r["ff"], r["dsp"]])
table(rows, [1.1, 0.5, 0.6, 0.6, 0.5], "TABLE III.  RESOURCES OF THE SIMD CORE (W = 16)")
para("LUT usage grows almost linearly with lanes (iCE40: %s → %s LUT4 from 1 to 4 lanes, %.1f× area for %.2f× speed-up), so area efficiency is roughly constant. "
     "Flip-flops grow less than linearly because the control unit and scalar register are shared. The 16 × 16-bit multiplier dominates a lane on LUT-only devices; with hard DSP multipliers "
     "(iCE40 UP5K, Xilinx DSP48E1) each lane uses one DSP and LUT usage falls (iCE40: %s LUT4 and 4 DSP at 4 lanes). The 8-lane LUT-multiplier build (%s LUT4) exceeds the HX8K (7,680 LUT4)."
     % (rs[("ice40", 1, 16)]["lut"], rs[("ice40", 4, 16)]["lut"], int(rs[("ice40", 4, 16)]["lut"]) / int(rs[("ice40", 1, 16)]["lut"]), sp(0, 4),
        rs[("ice40dsp", 4, 16)]["lut"], rs[("ice40", 8, 16)]["lut"]))
wide_begin()
figure("resources.png", 6.4, "Fig. 3. LUT, flip-flop and DSP usage of the SIMD core versus lane count.")
wide_end()
h2("D. Maximum frequency")
rows = [["Device", "1 lane", "2 lanes", "4 lanes"]]
for d, nm in (("hx8k", "iCE40 HX8K"), ("up5k", "iCE40 UP5K (DSP)")):
    rows.append([nm] + ["%.1f MHz" % fmax[(d, l, 16)] for l in (1, 2, 4)])
table(rows, [1.4, 0.7, 0.7, 0.7], "TABLE IV.  Fmax (nextpnr, BEST OF 4 SEEDS, W = 16)")
v1, v2 = cmpv[("v1", 4)], cmpv[("v2", 4)]
para("Fmax is almost independent of lane count (HX8K: %.1f → %.1f MHz, −%.0f %%), because lanes are parallel and only the shared register-read and result paths see added fan-out. "
     "Combined with the cycle counts, the wall-clock speed-up of the mixed kernel on HX8K is %.2f× for four lanes (%.2f× for two). "
     "Pre-decoding in stage F and pre-computing the bypass flags raised four-lane Fmax from %.1f to %.1f MHz (median %.1f → %.1f MHz, about +5 %%); at one lane the change was within placement noise. "
     "The remaining critical path is register read → ALU/carry chain → result mux, dominated by routing delay on the slow iCE40 fabric. Absolute frequencies are therefore specific to iCE40; "
     "[[if Vivado was run: report Artix-7 Fmax and utilisation here]]."
     % (fmax[("hx8k", 1, 16)], fmax[("hx8k", 4, 16)], 100 * (1 - fmax[("hx8k", 4, 16)] / fmax[("hx8k", 1, 16)]),
        (perf[(0, 1)] / fmax[("hx8k", 1, 16)]) / (perf[(0, 4)] / fmax[("hx8k", 4, 16)]),
        (perf[(0, 1)] / fmax[("hx8k", 1, 16)]) / (perf[(0, 2)] / fmax[("hx8k", 2, 16)]),
        float(v1["fmax_best"]), float(v2["fmax_best"]), float(v1["fmax_median"]), float(v2["fmax_median"])))

# ------------------------------------------------------------------ VI limits
h1("VI. Limitations")
para("(i) The load/store bus width scales with lane count, so memory bandwidth is not a bottleneck; a real system would be bandwidth-limited and show lower speed-up for low arithmetic-intensity kernels. "
     "(ii) N = 64 is small, so pipeline-fill overhead is visible. (iii) Frequencies come from iCE40 place-and-route and resources for Xilinx are a Yosys estimate, not Vivado results. "
     "(iv) The vector register file is built from flip-flops, which is the main flip-flop cost; block/distributed RAM would reduce it. (v) There are no divide, saturating, widening or masked-lane operations, and no vector-length register.")

# ------------------------------------------------------------------ VII contributions
h1("VII. Individual Contributions")
table([["Member", "Contribution"],
       ["[[Member 1]]", "[[e.g. lane ALU, lane MUXes, result combiner RTL]]"],
       ["[[Member 2]]", "[[e.g. register file, vector control unit, hazard/bypass unit, pipeline]]"],
       ["[[Member 3]]", "[[e.g. testbenches, coverage, mutation testing, golden vectors]]"],
       ["[[Member 4]]", "[[e.g. Digital Logic Sim SIMD_4LANE build and cross-check]]"],
       ["[[Member 5]]", "[[e.g. synthesis/Fmax study, scalar-vs-SIMD benchmarks, report, video]]"]],
      [1.0, 2.3], "TABLE V.  DIVISION OF WORK (EDIT TO MATCH ACTUAL CONTRIBUTIONS)", size=8)

# ------------------------------------------------------------------ VIII conclusion
h1("VIII. Conclusion")
para("A parameterised SIMD vector processing unit was designed, verified to a high standard and evaluated against a scalar baseline built from the same micro-architecture. "
     "Four lanes deliver %.2f× fewer cycles and %.2f× shorter execution time on an iCE40 HX8K for about %.1f× the logic, with near-constant Fmax, confirming that data-level parallelism "
     "scales almost ideally when memory bandwidth is not the limit. All sources, testbenches, scripts, results and the DLS design are in the project repository. "
     "Future work includes a vector-length register, masked execution, a banked memory model to quantify bandwidth limits, and Vivado implementation on an Artix-7 board."
     % (sp(0, 4), (perf[(0, 1)] / fmax[("hx8k", 1, 16)]) / (perf[(0, 4)] / fmax[("hx8k", 4, 16)]), int(rs[("ice40", 4, 16)]["lut"]) / int(rs[("ice40", 1, 16)]["lut"])))

# ------------------------------------------------------------------ references
h1("References")
refs = [
    "M. J. Flynn, “Some computer organizations and their effectiveness,” IEEE Trans. Comput., vol. C-21, no. 9, pp. 948–960, Sep. 1972.",
    "R. M. Russell, “The CRAY-1 computer system,” Commun. ACM, vol. 21, no. 1, pp. 63–72, Jan. 1978.",
    "J. L. Hennessy and D. A. Patterson, Computer Architecture: A Quantitative Approach, 6th ed. Morgan Kaufmann, 2019, ch. 4.",
    "R. B. Lee, “Subword parallelism with MAX-2,” IEEE Micro, vol. 16, no. 4, pp. 51–59, Aug. 1996.",
    "A. Peleg and U. Weiser, “MMX technology extension to the Intel architecture,” IEEE Micro, vol. 16, no. 4, pp. 42–50, Aug. 1996.",
    "RISC-V International, “RISC-V ‘V’ Vector Extension, Version 1.0,” 2021.",
    "J. Nickolls and W. J. Dally, “The GPU computing era,” IEEE Micro, vol. 30, no. 2, pp. 56–69, Mar./Apr. 2010.",
    "P. Yiannacouras, J. G. Steffan, and J. Rose, “VESPA: Portable, scalable, and flexible FPGA-based vector processors,” in Proc. Int. Conf. Compilers, Architectures and Synthesis for Embedded Systems (CASES), 2008, pp. 61–70.",
    "J. Yu, C. Eagleston, C. H.-Y. Chou, M. Perreault, and G. Lemieux, “Vector processing as a soft processor accelerator,” ACM Trans. Reconfigurable Technol. Syst., vol. 2, no. 2, pp. 12:1–12:34, 2009.",
    "D. Shah, E. Hung, C. Wolf, S. Bazanski, D. Gisselquist, and M. Milanović, “Yosys+nextpnr: An open source framework from Verilog to bitstream for commercial FPGAs,” in Proc. IEEE FCCM, 2019 (arXiv:1903.10407).",
    "S. Lague, “Digital Logic Sim,” software, github.com/SebLague/Digital-Logic-Sim.",
    "IEEE Standard for Verilog Hardware Description Language, IEEE Std 1364-2005, 2006.",
]
for i, r in enumerate(refs, 1):
    p = para("[%d]  %s" % (i, r), WD_ALIGN_PARAGRAPH.JUSTIFY, 8, False, False, False, after=1)
    p.paragraph_format.left_indent = Inches(0.3); p.paragraph_format.first_line_indent = Inches(-0.3)

out = os.path.join(ROOT, "report", "SIMD_VPU_IEEE_Report.docx")
doc.save(out)
print("wrote", out)
