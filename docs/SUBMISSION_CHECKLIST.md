# Submission checklist - what only the team can do

Rubric: Report 10 marks, Video 15 marks, GitHub 5 marks.

## A. Must-do (blocking)
- [ ] **Names / institute** - replace every yellow `[...]` placeholder in `report/SIMD_VPU_IEEE_Report.docx` (title block, section III-E, Table V "Individual Contributions", Fmax paragraph). Also fix `README.md` (team, video link).
- [ ] **Individual contributions** - edit Table V so each of the 5 members has a true, specific contribution (the draft split is only a suggestion).
- [ ] **Digital Logic Sim** - copy project into `dls/project/`, add screenshots to `dls/screenshots/`, fill `dls/README.md` + `docs/DLS_MAPPING.md`, do the cross-check from `vectors/DLS_TEST_SHEET_L4_W8.md` (or W16/other width) and write the outcome in the report (III-E and abstract).
- [ ] **Video** - record following `docs/VIDEO_SCRIPT.md` (<= 5:00, all 5 names, project idea, working demo). Upload, put the link in README + report.
- [ ] **Report** - open the .docx in **Word** (two-column layout was not visually verified outside Word), check figures/tables, remove highlights, export **PDF**, put both in `report/`.
- [ ] **GitHub** - repository public (or accessible to evaluators), link submitted through the form. Add all 5 members as collaborators and, ideally, let each commit their own part so the history shows individual work.

## B. Optional (raises quality)
- [ ] **Vivado** (if installed): synthesise `rtl/` with top `simd_vpu`, LANES=4 W=16 for an Artix-7; save utilisation + timing summaries to `results/vivado/` and add a row to the report's Table III/IV and README. Official Xilinx LUT/FF/DSP/Fmax numbers are stronger than our Yosys estimate.
- [ ] Run on a real board (iCE40/Artix-7) and film it - not required.
- [ ] Choose a licence (e.g. MIT) and add `LICENSE`.

## C. Facts to double-check yourselves
- References [1]-[12] in the report: we verified VESPA, VIPERS (TRETS 2009), Yosys+nextpnr and MAX-2 against online records; please also glance at the others (Flynn, Cray-1, Hennessy-Patterson, MMX, RISC-V V, Nickolls-Dally) and RISC-V V / DLS URLs before submitting.
- Everyone must be able to explain: lane ALU, bypass/hazard unit, why scalar = LANES 1, why speed-up < ideal, what mutation testing shows.
