# Digital Logic Sim - SIMD_4LANE

This folder holds the **gate-level 4-lane SIMD chip** built in Sebastian Lague's *Digital Logic Sim* (DLS).

## What to put here (team: please add)
1. **Project files** - copy your DLS project folder (the folder that contains the SIMD_4LANE chip and its sub-chips; DLS shows the project location under *Main Menu -> Manage Projects*). Commit it as `dls/project/`.
2. **Screenshots** in `dls/screenshots/` (suggested names):
   * `top_level.png` - the whole SIMD_4LANE chip
   * `lane.png` - one lane opened up (ALU + muxes)
   * `alu.png` - the ALU sub-chip internals
   * `demo_add.png`, `demo_cmp.png` ... - a test running (inputs set, 4 lane outputs showing at once)
3. Fill in the table below and `docs/DLS_MAPPING.md`.

## Facts about our DLS chip  (fill in)
| Item | Value |
|---|---|
| Lanes | 4 |
| Lane width | [[bits]] |
| Operations supported | [[e.g. ADD SUB AND OR + compare ...]] |
| Opcode encoding | [[bits -> operation]] |
| Registers / storage | [[none / latches / ...]] |
| DLS version | [[x.y]] |

## Cross-check procedure (about 15 minutes)
1. Open `vectors/DLS_TEST_SHEET_L4_W<width>.md` (generated for W=8 and W=16; regenerate for another width with
   `python3 scripts/gen_dls_vectors.py --lanes 4 --width <W>`).
2. For each row key operand A and B into the four lanes (lane 0 = least-significant lane), select the op, read the four result lanes.
3. Tick the "OK?" column. Any difference means the DLS chip implements a different convention (typical: shift amount, signed vs unsigned compare, compare result 1 vs all-ones) - note it in `docs/DLS_MAPPING.md`, it is a legitimate documented difference.
4. Record the outcome (e.g. "48/48 sampled vectors matched") in the report, section III-E, and in the video.
The identical vectors are replayed on the Verilog RTL in simulation (`make vectors`), so a match closes the loop RTL == model == DLS.
