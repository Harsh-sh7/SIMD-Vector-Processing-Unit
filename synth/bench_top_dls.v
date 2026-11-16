// Timing/synthesis wrapper for the DLS-style design (not part of the design): serial in, 1-bit parity out.
module bench_top_dls #(
    parameter LANES = 4
) (
    input  wire clk, din,
    output reg  dout
);
    localparam VW = 8 * LANES;
    localparam INW = 2*VW + 3 + 3;
    reg [INW-1:0] sh;
    always @(posedge clk) sh <= {sh[INW-2:0], din};

    wire [VW-1:0] result;
    simd_lanes #(.LANES(LANES)) u_core (
        .clk(clk), .load_a(sh[2*VW+3]), .load_b(sh[2*VW+4]), .result_en(sh[2*VW+5]),
        .opcode(sh[2*VW +: 3]), .a_in(sh[0 +: VW]), .b_in(sh[VW +: VW]), .result(result));

    localparam NP = (VW + 7) / 8;
    wire [NP*8-1:0] padded = {{(NP*8-VW){1'b0}}, result};
    reg [NP-1:0] par;
    integer p;
    always @(posedge clk) begin
        for (p = 0; p < NP; p = p + 1) par[p] <= ^padded[p*8 +: 8];
        dout <= ^par;
    end
endmodule
