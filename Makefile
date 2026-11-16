# SIMD Vector Processing Unit.  Requires: iverilog, yosys, nextpnr-ice40, python3
PY ?= python3

.PHONY: test mutation perf synth demo clean

test:      ## regression: exhaustive lane ALU + system testbench (8 configs) + golden-vector replay
	$(PY) scripts/run_tests.py

mutation:  ## inject 21 deliberate bugs, confirm the testbench catches each
	$(PY) scripts/run_mutation.py

perf:      ## scalar (1 lane) vs SIMD (2/4/8/16 lanes) cycle counts
	$(PY) scripts/run_perf.py

synth:     ## FPGA resources (iCE40, iCE40+DSP, Xilinx-7 estimate) and Fmax  (~10 min)
	$(PY) scripts/run_synth.py

demo:      ## cycle-by-cycle trace of the 4-lane run + scalar-vs-SIMD table
	iverilog -g2012 -I rtl -Ptb_perf.LANES=4 -Ptb_perf.N=16 -o build/demo.vvp tb/tb_perf.v rtl/*.v && vvp build/demo.vvp +trace | tail -40
	$(PY) scripts/run_perf.py

clean:
	rm -rf build
