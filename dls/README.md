# Digital Logic Sim - SIMD_4LANE

Gate-level 4-lane SIMD chip built in Sebastian Lague's Digital Logic Sim.

- `project/` - the DLS project folder (chip files)
- `screenshots/` - top level, one lane, ALU, a running test

| Item | Value |
|---|---|
| Lanes | 4 |
| Lane width | [bits] |
| Operations | [list] |

**Cross-check:** key the operands from `vectors/DLS_TEST_SHEET_L4_W8.md` (or `_W16`) into the chip and compare each lane with the EXPECTED column.
The same vectors are verified against the Verilog RTL by `make test`. Regenerate for another width: `python3 scripts/gen_dls_vectors.py --lanes 4 --width <W>`.
