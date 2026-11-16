// -----------------------------------------------------------------------------
// scalar_baseline : the scalar reference design = the SAME micro-architecture,
// ISA and workload program as simd_vpu but with exactly ONE lane. Comparing it
// with the multi-lane build isolates the effect of data-level parallelism
// (same pipeline, same ISA, same clocking - only the number of lanes differs).
// -----------------------------------------------------------------------------
module scalar_baseline #(
    parameter W = 16
) (
    input  wire         clk,
    input  wire         rst,
    input  wire         instr_valid,
    input  wire [31:0]  instr,
    input  wire [W-1:0] ld_data,
    input  wire         scalar_we,
    input  wire [W-1:0] scalar_in,
    output wire         st_valid,
    output wire [W-1:0] st_data,
    output wire         sc_valid,
    output wire [W-1:0] scalar_out,
    output wire         flags_valid,
    output wire         vmask,
    output wire         vany,
    output wire         vall,
    input  wire         perf_clr,
    output wire [31:0]  perf_cycles,
    output wire [31:0]  perf_instr,
    output wire [31:0]  perf_laneops
);
    simd_vpu #(.LANES(1), .W(W)) u_core (
        .clk(clk), .rst(rst), .instr_valid(instr_valid), .instr(instr),
        .ld_data(ld_data), .scalar_we(scalar_we), .scalar_in(scalar_in),
        .st_valid(st_valid), .st_data(st_data), .sc_valid(sc_valid),
        .scalar_out(scalar_out), .flags_valid(flags_valid), .vmask(vmask),
        .vany(vany), .vall(vall), .perf_clr(perf_clr), .perf_cycles(perf_cycles),
        .perf_instr(perf_instr), .perf_laneops(perf_laneops)
    );
endmodule

// (reviewed: port widths / params consistent with simd_defs.vh)
