# Digital Logic Sim design - `SIMD_4LANE`

A gate-level **4-lane x 8-bit SIMD unit** (32-bit vectors) built bottom-up in Sebastian Lague's *Digital Logic Sim*.
One instruction (a 3-bit opcode) drives **four identical 8-bit ALUs** that process four byte-lanes of two operand vectors **in parallel**.
Every chip below has a Verilog counterpart in [`../dls_rtl/`](../dls_rtl/) that is verified against the screenshots in this folder.

```
 A[4 x 8 bit] --\                                                   /--> RESULT-REGISTER-FILE --> R[4 x 8 bit]
                 >-- VECTOR-REGISTER-FILE --> 4 x 8-Bit-ALU (parallel) --/
 B[4 x 8 bit] --/        (8 registers)            ^ opcode (3 bits, shared)     (4 registers)
```

## 1. Top level - `SIMD_4LANE`
![SIMD_4LANE](screenshots/01_simd_4lane_top.png)

* **Inputs (left):** operand vector **A** = 10, 20, 30, 40 and operand vector **B** = 1, 2, 3, 4 (eight 8-bit inputs), four single-bit control inputs (`LOAD-A`, `LOAD-B`, `Clk`, `RESULT_WRITE`), and a 4-bit input `IN` that carries the opcode. A `4-1BIT` splitter turns it into single wires: three of them (S2, S1, S0) go to all four ALUs; the fourth wire is unused (DLS only offers 4-bit inputs, the design needs 3).
* **VECTOR-REGISTER-FILE** (green) stores A and B. Its outputs feed the **four `8-Bit-ALU`** chips (lane 0-3) - each lane receives one byte of A and the matching byte of B.
* **RESULT-REGISTER-FILE** (purple) captures the four lane results.
* **Outputs (right):** 9, 18, 27, 36 = A - B lane by lane (opcode SUB). Four subtractions happened in the same step.

## 2. Lane datapath - `8-Bit-ALU` (one lane, six operations)
Five operator chips and a comparator all see the same inputs A and B; the **`8-1-MUX(8-Bit)`** picks one result with the 3-bit opcode (the three select bulbs at the bottom).

| Opcode (S2 S1 S0) | Operation | Chip | Screenshot test (A, B -> result) |
|:--:|---|---|---|
| `000` | ADD | `8-Bit-RC-ADDER` | 64 + 96 = **160** |
| `001` | SUB | `8-Bit-SUBTRACTOR` | 112 - 96 = **16** |
| `010` | AND | `8-Bit-AND` | 96 & 112 = **96** |
| `011` | OR | `8-Bit-OR` | 96 \| 112 = **112** |
| `100` | XOR | `8-Bit-XOR` | 96 ^ 112 = **16** |
| `101` | COMPARE | `COMPARE` -> `1BIT-8BIT` | 112 vs 112 -> **255** (equal); different values -> **0** |
| `110`, `111` | reserved | mux inputs unconnected | do nothing yet |

| ADD `000` | SUB `001` | AND `010` |
|---|---|---|
| ![](screenshots/05_alu_add.png) | ![](screenshots/06_alu_sub.png) | ![](screenshots/07_alu_and.png) |

| OR `011` | XOR `100` | COMPARE `101` |
|---|---|---|
| ![](screenshots/08_alu_or.png) | ![](screenshots/09_alu_xor.png) | ![](screenshots/10_alu_compare.png) |

(The opcode values were read directly from the lit/unlit select bulbs in these screenshots, top bulb = most significant bit.)
`COMPARE` is an `8-Bit-SUBTRACTOR` followed by an `8-1-ZERO` detector, so it produces 1 when A - B = 0, i.e. when A = B. `1BIT-8BIT` copies that bit into all eight bits, so equal -> 255 and not equal -> 0, usable as a lane mask.

## 3. Storage
| Chip | Screenshot | What it is |
|---|---|---|
| `VECTOR-REGISTER-FILE` | ![](screenshots/03_vector_register_file.png) | **8** x `8-Bit-REGISTER_EN` = 4 bytes of operand A + 4 bytes of operand B; three control inputs |
| `RESULT-REGISTER-FILE` | ![](screenshots/02_result_register_file.png) | **4** x `8-Bit-REGISTER_EN` = the four lane results; two control inputs |
| `8-Bit-REGISTER_EN` | ![](screenshots/04_register8_en_internals.png) | `8-1BIT` splitter -> **8** x `D-FLIP-FLOP-EN` -> `1-8BIT` merger (value 53 stored in the screenshot) |

## 4. Chip library (bottom-up build)
![library](screenshots/dls_library.png)

`FULL_ADDER` -> `8-Bit-RC-ADDER` -> `8-Bit-SUBTRACTOR` (collection `ADDER_SUBTRACTOR`) | `8-Bit-AND/OR/XOR` (`8-Bit-OPERATORS`) | `2-1-MUX`, `2-1-DEMUX`, `8-1-MUX`, `2-1-MUX(8-Bit)`, `8-1-MUX(8-Bit)` (`MUXES`) |
`8-Bit-ALU` | `D-Latch` -> `D-FLIP-FLOP` -> `D-FLIP-FLOP-EN` -> `8-Bit-REGISTER` / `8-Bit-REGISTER_EN` (`REGISTER-COMPONENTS`) | `32-Bit_Input`, `VECTOR-REGISTER-FILE`, `RESULT-REGISTER-FILE`, `SIMD_4LANE`.

## 5. DLS chip -> Verilog module (all in `dls_rtl/`)

| DLS chip | Verilog file / module |
|---|---|
| `FULL_ADDER` | `full_adder.v` / `full_adder` |
| `8-Bit-RC-ADDER` | `rc_adder8.v` / `rc_adder8` (8 x full_adder, ripple carry) |
| `8-Bit-SUBTRACTOR` | `subtractor8.v` / `subtractor8` (a + ~b + 1) |
| `8-Bit-AND / OR / XOR` | `bitwise8.v` / `and8`, `or8`, `xor8` |
| `COMPARE`, `1BIT-8BIT` | `compare8.v` / `compare8`, `bit_to_byte` |
| `8-1-MUX(8-Bit)` | `mux8to1_8bit.v` |
| **`8-Bit-ALU`** | `alu8.v` / `alu8` |
| `D-FLIP-FLOP-EN`, `8-Bit-REGISTER_EN` | `registers.v` / `dff_en`, `register8_en` |
| `VECTOR-REGISTER-FILE`, `RESULT-REGISTER-FILE` | `register_files.v` |
| **`SIMD_4LANE`** | `simd_lanes.v` / `simd_4lane` (`simd_lanes` is the same design with a `LANES` parameter; `LANES = 1` is the scalar baseline) |

## 6. Evidence that the Verilog equals the DLS chip
Run `make dls` (about 30 s). Output (abridged):
```
ALU ADD  opcode=000  A= 64  B= 96  ->  160   (DLS screenshot shows 160)  MATCH      ... SUB, AND, OR, XOR, CMP the same
SIMD_4LANE  SUB  [10,20,30,40] - [1,2,3,4]  ->  [9,18,27,36]   (DLS screenshot shows 9,18,27,36)  MATCH
enable gating: registers hold when disabled, A and B load independently   OK
524,288 exhaustive ALU checks, 393,216 equivalence checks vs rtl/lane_alu.v, 4,000 random full-chip passes   -> DLS MIRROR TESTS PASSED
mutation check: 9 / 9 injected bugs detected          scalar 66 cycles vs 4 lanes 18 cycles (64 elements) = 3.67x
```
Full numbers (cycles, FPGA resources, Fmax): [`../results/DLS_MIRROR_RESULTS.md`](../results/DLS_MIRROR_RESULTS.md).

## 7. Design facts (confirmed by the design owner and checked against the project files)
| # | Item | Fact |
|---|---|---|
| 1 | What `COMPARE` tests | **Equality.** 255 when A = B, 0 when A != B. Built as `8-Bit-SUBTRACTOR` -> `8-1-ZERO` -> `1BIT-8BIT`. |
| 2 | Control inputs of `SIMD_4LANE` | `Clk` is the clock; `LOAD-A` and `LOAD-B` are write enables of the A and B registers; `RESULT_WRITE` is the write enable of the result registers. |
| 3 | The 4-bit input `IN` and the `4-1BIT` chip | `IN` carries the opcode. The simulator only offers a 4-bit input, the design needs 3 bits, so one bit is unused. `4-1BIT` is a splitter: 3 of its 4 outputs drive S2, S1, S0 of the four ALUs. |
| 4 | Opcodes `110` / `111` | Reserved, do nothing yet (mux inputs unconnected; the Verilog outputs 0). |

## 8. The Digital Logic Sim project files
[`project/`](project/) is the complete Digital Logic Sim save (`SIMD_Processing_Unit`, DLS 2.1.6): `ProjectDescription.json` and `Chips/*.json`, one file per chip (31 chips including `SIMD_4LANE`).
To open it: install Digital Logic Sim, copy the `SIMD_Processing_Unit` folder into its `Projects` folder (on macOS `~/Library/Application Support/com.DefaultCompany.2DProject/Projects/`), start the game and choose the project in the project list.

## 9. Demo procedure for the video (about 75 s)
1. Open `SIMD_4LANE`; set A = 10, 20, 30, 40 and B = 1, 2, 3, 4; opcode `001` (SUB); pulse load, then the result enable -> outputs 9, 18, 27, 36.
2. Change the opcode to ADD (`000`) -> 11, 22, 33, 44; AND/OR/XOR if you like.
3. Open `8-Bit-ALU`: show the 3-bit select and the six results (64+96=160, 112-96=16, 96&112=96, 96|112=112, 96^112=16, 112==112 -> 255).
4. Open `VECTOR-REGISTER-FILE` (8 registers) and `RESULT-REGISTER-FILE` (4 registers), then one `8-Bit-REGISTER_EN` (8 flip-flops).
