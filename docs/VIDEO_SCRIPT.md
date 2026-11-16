# 5-minute demo video - shot list and spoken script (hard limit 5:00, aim for 4:40)

Brief requirements: state the **project idea**, **introduce all 5 members by name**, **demonstrate the working prototype**.
Five speakers, one block each. Record with QuickTime (File -> New Screen Recording) or OBS. Replace `[Name]` with the real names.
Run `make dls test perf` once beforehand so nothing compiles for the first time on camera.

| Time | Speaker | On screen | Spoken script |
|---|---|---|---|
| **0:00-0:35** | [Name 1] | Title slide / GitHub README | "Hello, we are [Name 1], [Name 2], [Name 3], [Name 4] and [Name 5]. Our project is number 11, the **SIMD Vector Processing Unit**. SIMD means Single Instruction, Multiple Data: one instruction operates on many data elements at the same time. We built a 4-lane SIMD chip from logic gates in Digital Logic Sim, rebuilt it in Verilog, and measured how much faster it is than a scalar processor." |
| **0:35-1:10** | [Name 2] | `dls/screenshots/01_simd_4lane_top.png` (or live DLS top level) | "A scalar unit adds one pair of numbers per step. Our unit has **four identical 8-bit ALUs** fed from a vector register file, so one 32-bit vector holds four bytes and all four are processed together. Operands go into the VECTOR-REGISTER-FILE, four ALUs compute in parallel, and the RESULT-REGISTER-FILE holds the four results. One shared 3-bit opcode selects the operation." |
| **1:10-2:30** | [Name 3] | **Digital Logic Sim, live** | **(a)** Top level: A = 10,20,30,40, B = 1,2,3,4, opcode 001 (SUB). Load, then result: "9, 18, 27, 36 - four subtractions in one step." Change to ADD: 11,22,33,44. **(b)** Open `8-Bit-ALU`: "Five operator chips and a comparator feed an 8-to-1 multiplexer chosen by three select bits: 000 add, 001 subtract, 010 AND, 011 OR, 100 XOR, 101 compare." Show 64+96=160, 112-96=16, 96&112=96, 96\|112=112, 96^112=16, 112==112 gives 255. **(c)** Open VECTOR-REGISTER-FILE (8 registers) and RESULT-REGISTER-FILE (4), then one 8-Bit-REGISTER_EN: "eight D flip-flops with enable." Mention the bottom-up library (full adder, ripple adder, mux, latch, flip-flop...). |
| **2:30-3:20** | [Name 4] | VS Code `dls_rtl/` (alu8.v, simd_lanes.v) then terminal `make dls` | "We wrote a Verilog module for every DLS chip: full adder, ripple adder, subtractor, ALU, register, register files and the top level. Running `make dls` replays the exact cases from the simulator - ADD 160, SUB 16, AND 96, OR 112, XOR 16, compare 255, and the vector subtract 9, 18, 27, 36 - all match. It also runs 524 thousand exhaustive ALU checks, proves equivalence with our generalised RTL, and injects nine bugs that the tests all catch." |
| **3:20-4:10** | [Name 5] | `results/DLS_MIRROR_RESULTS.md`, `docs/img/speedup.png`, `make perf` output | "Same workload, 64 elements: **scalar, one lane, 66 cycles; four lanes, 18 cycles - 3.67 times faster**; 8 lanes 6.6 times, 16 lanes 11 times. The gap to the ideal is the two-cycle pipeline fill. Our generalised pipelined RTL with 16 operations gives 515 versus 131 cycles, 3.93 times, and 3.69 times in real time on an iCE40 FPGA." |
| **4:10-4:45** | [Name 5] | `docs/img/resources.png`, `results/RESULTS.md` | "Area grows almost linearly with lanes: the 4-lane DLS-style design needs only 257 LUTs and 96 flip-flops and runs at about 160 MHz on an iCE40 HX8K; the full RTL uses 4041 LUTs. Frequency barely drops when lanes are added, so the speed-up is real." |
| **4:45-5:00** | All (one by one) | GitHub repo page | "Everything - RTL, testbenches, DLS screenshots, report and results - is in our GitHub repository linked in the submission. Thank you." |

## Recording tips
* Keep the DLS window zoomed so the opcode bulbs and the numbers are readable.
* Do the DLS demo first on a rehearsal take; pre-set inputs so you only toggle the buttons.
* Rehearse with a timer; cut rather than rush. Upload as YouTube *unlisted* or Google Drive (anyone with link) and paste the URL in `README.md` and the report.
