# Architecture notes

## Modules
| Module | Role |
|---|---|
| `lane_alu` | One W-bit ALU, 16 ops (see table). Combinational. |
| `simd_lane` | Lane operand MUX (vreg lane / broadcast scalar) -> `lane_alu` -> result MUX (ALU / load / splat) |
| `vreg_file` | 8 x (LANES*W) registers, 2 async read ports, 1 write port, bypass muxes (select = registered flag) |
| `vec_ctrl` | Stage-F decode into registered controls; hazard unit (`byp1/byp2`); perf counters |
| `result_combiner` | Packs lane results; predicate mask (LSB per lane), ANY / ALL reductions |
| `simd_vpu` | Top: `ld_q` capture, scalar register, `generate` of LANES lanes, E->W registers, VST/VEXT/flag outputs |
| `scalar_baseline` | `simd_vpu` with LANES = 1 |

## Lane operations
`0 ADD, 1 SUB, 2 AND, 3 OR, 4 XOR, 5 SLL, 6 SRL, 7 SRA, 8 MUL(low W bits), 9 EQ, A NE, B LT(s), C GT(s), D LTU, E MIN(s), F MAX(s)`.
Shift amount = low log2(W) bits of operand B. Compare results are all-ones (true) / 0 (false) per lane.

## Instruction classes
`0 NOP, 1 VV, 2 VS, 3 VLD, 4 VST, 5 VSPLAT, 6 SSET (sreg = sign-extended imm), 7 VEXT (scalar_out = lane[imm] of vs1)`.

## Interface timing (instruction presented in cycle t)
* `ld_data` must be presented **in the same cycle** as the VLD instruction (captured into `ld_q`).
* Register write happens at the end of cycle t+2; a dependent instruction issued in t+1 sees the data through the bypass (no stall).
* `st_valid/st_data` (VST), `sc_valid/scalar_out` (VEXT) and `flags_valid/vmask/vany/vall` (VV/VS ops) are registered and appear after the edge ending cycle t+1 (i.e. visible in cycle t+2).
* External scalar write (`scalar_we`) takes priority over an `SSET` in the same cycle.

## Hazards
Only RAW through the register file exists because the pipeline is in-order with a single write port. The hazard unit compares the source fields of the instruction in F with the destination of the instruction in E and registers `byp1/byp2`; the E-stage read mux then selects the write-back data. WAW needs no handling (in-order write). This was verified at RAW distance 1/2/3, WAW and self-dependency, and by mutation (removing the bypass or breaking the comparison is detected).

## Design-space parameters
`LANES` (any >= 1; `VEXT` index compared against all lanes) and `W` (>= 8 tested up to 32). `make synth` sweeps LANES 1/2/4/8(/16) and W 8/16/32.
