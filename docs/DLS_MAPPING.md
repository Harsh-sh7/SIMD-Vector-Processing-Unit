# Mapping: Digital Logic Sim chip  <->  Verilog modules

Fill the right-hand column with the names of your DLS chips. This table is useful for the report (section III-E) and the video.

| Concept | Verilog module | DLS chip / part |
|---|---|---|
| One arithmetic/logic lane | `lane_alu` | [[ALU chip name]] |
| Operand-B select (vector vs scalar) | `simd_lane` (mux) | [[mux chip, or "not implemented"]] |
| Lane replication (data-level parallelism) | `generate` loop in `simd_vpu` | [[4 copies of the ALU chip]] |
| Operation select / opcode decode | `vec_ctrl` | [[opcode decoder chip]] |
| Vector register file | `vreg_file` | [[registers/latches, or "inputs set by hand"]] |
| Result combiner / output bus | `result_combiner` | [[output wiring / bus]] |
| Compare flags | `vmask / vany / vall` | [[flag outputs]] |

## Known convention differences to check (RTL vs DLS)
* Compare result: RTL returns **all-ones** (e.g. 0xFF) for true; a DLS chip may return 1 in the LSB only.
* Shift amount: RTL uses `B mod W` (low log2(W) bits of B).
* `LT/GT/MIN/MAX` are **signed**; `LTU` is unsigned.
* Overflow: results wrap modulo 2^W (no saturation); `MUL` keeps the low W bits.

## Why both?
The DLS chip shows the *structure* (four identical ALUs fed by one control word) from primitive gates; the Verilog gives the parameterisable, verifiable, synthesizable version with measurable performance. The golden-vector sheet proves they compute the same function.
