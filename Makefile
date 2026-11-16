# SIMD Vector Processing Unit - one-command flows.   Requires: iverilog, yosys, nextpnr-ice40, python3 + matplotlib
PY ?= python3

.PHONY: all test vectors mutation perf synth fmax-compare plots diagrams waveform demo clean

all: test mutation perf synth fmax-compare plots diagrams waveform   ## everything (synth takes ~10 min)

test:          ## regression: exhaustive lane ALU + system TB over 8 configs + golden-vector replay
	$(PY) scripts/run_tests.py

vectors:       ## regenerate the DLS cross-check vectors (and replay them against the RTL)
	$(PY) scripts/gen_dls_vectors.py --lanes 4 --width 8
	$(PY) scripts/gen_dls_vectors.py --lanes 4 --width 16
	$(PY) scripts/run_tests.py

mutation:      ## inject 21 deliberate bugs and confirm the testbench catches each one
	$(PY) scripts/run_mutation.py

perf:          ## scalar (1 lane) vs SIMD (2/4/8/16 lanes) cycle counts, 3 kernels
	$(PY) scripts/run_perf.py

synth:         ## resource utilisation (iCE40, iCE40+DSP, Xilinx-7 estimate) and Fmax (nextpnr)
	$(PY) scripts/run_synth.py

fmax-compare:  ## v1 vs final RTL Fmax
	$(PY) scripts/run_fmax_compare.py

plots:         ## figures + results/RESULTS.md from the CSVs
	$(PY) scripts/make_plots.py

diagrams:
	$(PY) scripts/make_diagrams.py

waveform:      ## short demo run -> results/perf_demo.vcd + docs/img/waveform.png
	$(PY) scripts/plot_waveform.py

demo:          ## what to run in the video: cycle-by-cycle trace of the 4-lane run + scalar-vs-SIMD summary
	iverilog -g2012 -I rtl -Ptb_perf.LANES=4 -Ptb_perf.N=16 -o build/demo.vvp tb/tb_perf.v rtl/*.v && vvp build/demo.vvp +trace | tail -40
	$(PY) scripts/run_perf.py

clean:
	rm -rf build
