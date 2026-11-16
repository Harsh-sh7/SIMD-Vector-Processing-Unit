# Vivado run (optional, for real Artix-7 numbers)

The report's Xilinx figures are Yosys estimates. This script produces real Vivado numbers.

1. Install Vivado (the free *WebPACK / Standard* edition is enough; Windows or Linux).
2. Open a terminal, `cd` to the repository root, and run `vivado -mode batch -source synth/vivado/run_vivado.tcl`.
   (On Windows use the *Vivado Tcl Shell* or `vivado.bat`.) It takes about 10-30 minutes.
3. Open `results/vivado/vivado_results.csv` (LUT, FF, DSP, Fmax for the DLS-style design with 1, 2, 4, 8 lanes and the generalised core with 1 and 4 lanes) and send it to whoever edits the report.

Notes: the part is `xc7a35tcpg236-1` (Basys-3); change `set part` at the top of the script for another board. The script was written without access to Vivado, so if a command errors, send the error text.
