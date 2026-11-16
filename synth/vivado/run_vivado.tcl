# Vivado batch script: Artix-7 utilisation and Fmax for the DLS-style design and the generalised core.
#
#   cd <repo root>
#   vivado -mode batch -source synth/vivado/run_vivado.tcl
#
# Result: results/vivado/vivado_results.csv  (+ one utilisation / timing report per run in results/vivado/)
# Part: xc7a35tcpg236-1 (Digital Blocks Basys-3 Artix-7).  Change $part if you use another board.
# util_*  = core alone, out-of-context synthesis (no I/O wrapper)  -> LUT / FF / DSP numbers
# fmax_*  = synth/bench_top*.v wrapper, synthesis + place + route    -> Fmax = 1000 / (period - WNS)

set root   [file normalize [file join [file dirname [info script]] .. ..]]
set part   xc7a35tcpg236-1
set period 4.0
set out    [file join $root results vivado]
file mkdir $out
set csv [open [file join $out vivado_results.csv] w]
puts $csv "design,lanes,w,lut,ff,dsp,fmax_mhz"

set dls_files [glob [file join $root dls_rtl *.v]]
set gen_files [glob [file join $root rtl *.v]]
set incdir    [file join $root rtl]

proc count_cell {util_file pattern} {
    # first number in the 'Used' column of the report line that starts with the pattern
    set fh [open $util_file]; set txt [read $fh]; close $fh
    foreach line [split $txt "\n"] {
        if {[regexp "^\\|\\s*$pattern\\s*\\|\\s*(\\d+)" $line -> n]} { return $n }
    }
    return -1
}

proc run_design {tag files top util_top bench lanes w generics} {
    global part period out root incdir csv
    # ---- utilisation: core alone, out-of-context
    read_verilog $files
    synth_design -top $util_top -part $part -mode out_of_context -include_dirs $incdir {*}$generics
    set uf [file join $out util_$tag.rpt]
    report_utilization -file $uf
    set lut [count_cell $uf "Slice LUTs\\*?"]
    set ff  [count_cell $uf "Slice Registers"]
    set dsp [count_cell $uf "DSPs"]
    close_project -quiet
    # ---- Fmax: wrapper, full implementation
    read_verilog $files
    read_verilog $bench
    synth_design -top $top -part $part -include_dirs $incdir {*}$generics
    set xdc [file join $out clk.xdc]
    set fx [open $xdc w]; puts $fx "create_clock -period $period \[get_ports clk\]"; close $fx
    read_xdc $xdc
    opt_design; place_design; route_design
    report_timing_summary -file [file join $out timing_$tag.rpt]
    set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
    set fmax [expr {1000.0 / ($period - $wns)}]
    puts $csv "$tag,$lanes,$w,$lut,$ff,$dsp,[format %.1f $fmax]"
    flush $csv
    close_project -quiet
}

foreach l {1 2 4 8} {
    run_design dls_L$l $dls_files bench_top_dls simd_lanes \
        [file join $root synth bench_top_dls.v] $l 8 [list -generic LANES=$l]
}
foreach l {1 4} {
    run_design gen_L${l}_W16 $gen_files bench_top simd_vpu \
        [file join $root synth bench_top.v] $l 16 [list -generic LANES=$l -generic W=16]
}
close $csv
puts "DONE: see $out/vivado_results.csv"
