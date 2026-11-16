# 5-minute demo video - script and shot list  (hard limit 5:00 - aim for 4:40)

Requirements from the brief: clearly state the **project idea**, **introduce all 5 members by name**, **demonstrate the working prototype**.
Record the screen with QuickTime (File -> New Screen Recording) or OBS; each member speaks one part.

| Time | Who | On screen | Say |
|---|---|---|---|
| 0:00-0:35 | Member 1 | Title slide / README top | "Project 11: SIMD Vector Processing Unit. One instruction, many data elements: we built a 4-lane SIMD unit in Verilog, a gate-level 4-lane version in Digital Logic Sim, and measured speed-up against a scalar version." **All five names + one-line role each.** |
| 0:35-1:15 | Member 2 | `docs/img/block_diagram.png` | Explain: 4 identical lanes, vector register file, control unit, lane muxes (vector vs broadcast scalar), result combiner. Pipeline: 1 instruction/cycle, bypass, no stalls. |
| 1:15-2:00 | Member 3 | **Digital Logic Sim** SIMD_4LANE, live | Set A and B on four lanes, choose ADD, show 4 results at once; switch to compare; show one lane opened (ALU). Say lane width and ops. Mention cross-check sheet result (e.g. "N/N vectors matched RTL"). |
| 2:00-2:50 | Member 4 | VS Code: `rtl/lane_alu.v`, `simd_vpu.v` (generate loop), then terminal `make test` | Show the generate loop = parallel lanes. Run `make test` (speed up the recording or cut to the PASS lines): 1,048,576 exhaustive checks, 8 configurations, REGRESSION PASSED. Mention `make mutation` 21/21 bugs caught. |
| 2:50-3:30 | Member 4 | `docs/img/waveform.png` (or GTKWave/Surfer on `results/perf_demo.vcd`) + `make demo` output | Point out: all 4 lane results change in the same cycle; one instruction per cycle; dependent instructions back-to-back. |
| 3:30-4:15 | Member 5 | `make perf` output + `docs/img/speedup.png` | Same program: **scalar 515 cycles, 4-lane 131 cycles = 3.93x**; 2/8/16 lanes 1.99x / 7.69x / 14.71x. Wall-clock 3.69x on iCE40 at 47 vs 44 MHz. Explain the 2-cycle fill. |
| 4:15-4:45 | Member 5 | `docs/img/resources.png`, `results/RESULTS.md` | 4 lanes: 4041 LUT4 / 883 FF on iCE40; 1990 LUT / 4 DSP on Xilinx estimate; area grows ~linearly with lanes, Fmax stays ~constant. |
| 4:45-5:00 | All | README / repo URL | "Everything is in our GitHub repository - link in the submission form." Thank you. |

## Before recording
* `make test perf demo` once so nothing compiles for the first time on camera.
* Close unrelated windows; font size 16+ in terminal/editor; keep the DLS window at a readable zoom.
* Rehearse once with a timer. Cut, don't rush.
* Upload (YouTube *unlisted* or Google Drive with link access) and paste the link into `README.md` and the report.
