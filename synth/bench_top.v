// -----------------------------------------------------------------------------
// bench_top : synthesis / timing wrapper (NOT part of the design under evaluation)
//
// The SIMD unit has ~300 I/O bits, more than a small FPGA has pins and far more than
// is meaningful for an internal-timing measurement. This wrapper feeds the core from
// a serial shift register (1 input pin) and folds every core output into a 1-bit
// registered parity (1 output pin), so (a) nothing is optimised away and (b) the
// critical path reported by place-and-route is the core's internal path, not pad delay.
// Resource numbers in the report are taken from simd_vpu ALONE (without this wrapper).
// -----------------------------------------------------------------------------
module bench_top #(
    parameter LANES = 4,
    parameter W     = 16
) (
    input  wire clk,
    input  wire rst,
    input  wire din,
    output reg  dout
);
    localparam VW   = LANES * W;
    localparam INW  = 32 + VW + W + 2 + 1;          // instr, ld, scalar_in, valid, we, perf_clr
    reg [INW-1:0] sh;
    always @(posedge clk) sh <= {sh[INW-2:0], din};

    wire [31:0]    instr       = sh[31:0];
    wire [VW-1:0]  ld_data     = sh[32 +: VW];
    wire [W-1:0]   scalar_in   = sh[32+VW +: W];
    wire           instr_valid = sh[32+VW+W];
    wire           scalar_we   = sh[32+VW+W+1];
    wire           perf_clr    = sh[32+VW+W+2];

    wire           st_valid, sc_valid, flags_valid, vany, vall;
    wire [VW-1:0]  st_data;
    wire [W-1:0]   scalar_out;
    wire [LANES-1:0] vmask;
    wire [31:0]    perf_cycles, perf_instr, perf_laneops;

    simd_vpu #(.LANES(LANES), .W(W)) u_core (
        .clk(clk), .rst(rst), .instr_valid(instr_valid), .instr(instr),
        .ld_data(ld_data), .scalar_we(scalar_we), .scalar_in(scalar_in),
        .st_valid(st_valid), .st_data(st_data), .sc_valid(sc_valid),
        .scalar_out(scalar_out), .flags_valid(flags_valid), .vmask(vmask),
        .vany(vany), .vall(vall), .perf_clr(perf_clr),
        .perf_cycles(perf_cycles), .perf_instr(perf_instr), .perf_laneops(perf_laneops));

    // fold all outputs into 16 partial parities (registered), then one final parity (registered)
    wire [VW+W+LANES+3+3+96-1:0] all_out = {st_data, scalar_out, vmask, st_valid, sc_valid, flags_valid,
                                            vany, vall, 1'b0, perf_cycles, perf_instr, perf_laneops};
    localparam OW = VW+W+LANES+3+3+96;
    localparam NP = (OW + 15) / 16;
    wire [NP*16-1:0] padded = {{(NP*16-OW){1'b0}}, all_out};
    reg  [NP-1:0] par;
    integer p;
    always @(posedge clk) begin
        for (p = 0; p < NP; p = p + 1) par[p] <= ^padded[p*16 +: 16];
        dout <= ^par;
    end
endmodule
