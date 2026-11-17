// -----------------------------------------------------------------------------
// tb_dls_perf : scalar (LANES = 1) vs SIMD (LANES = 2/4/8/16) cycle count for the DLS-style design.
// Workload: N element-wise operations; the opcode changes every pass (ADD, SUB, AND, OR, XOR, COMPARE, ...).
// Each pass processes LANES elements, so P = N / LANES passes. Streaming mode: one pass per clock.
// Prints:  DLSPERF,<lanes>,<N>,<cycles>,<passes>,<correct>
//   iverilog -Ptb_dls_perf.LANES=4 ...
// -----------------------------------------------------------------------------
`timescale 1ns/1ps

module tb_dls_perf;
    parameter LANES = 4;
    parameter N     = 64;
    localparam P    = N / LANES;
    localparam VW   = 8 * LANES;

    reg clk = 0, load_a = 0, load_b = 0, result_en = 0;
    reg [2:0] opcode = 0;
    reg [VW-1:0] a_in = 0, b_in = 0;
    wire [VW-1:0] result;
    simd_lanes #(.LANES(LANES)) dut (.clk(clk), .load_a(load_a), .load_b(load_b), .result_en(result_en),
                                    .opcode(opcode), .a_in(a_in), .b_in(b_in), .result(result));
    always #5 clk = ~clk;

    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    function [7:0] ref8;
        input [2:0] o; input [7:0] x, z;
        case (o)
            3'd0: ref8 = x + z;   3'd1: ref8 = x - z;   3'd2: ref8 = x & z;
            3'd3: ref8 = x | z;   3'd4: ref8 = x ^ z;   default: ref8 = (x == z) ? 8'hFF : 8'h00;
        endcase
    endfunction

    reg [7:0] ma [0:N-1];  reg [7:0] mb [0:N-1];
    integer i, c, l, errors = 0, first_cyc = -1, last_cyc = -1;
    reg [2:0] pop;

    initial begin
        for (i = 0; i < N; i = i + 1) begin ma[i] = $random; mb[i] = (i % 5 == 0) ? ma[i] : $random; end
        repeat (3) @(posedge clk);
        #1 load_a = 1; load_b = 1; result_en = 1;
        for (c = 0; c <= P + 1; c = c + 1) begin
            @(posedge clk); #1;
            if (c >= 2) begin                                   // result of pass c-2 is now visible
                pop = (c - 2) % 6;
                for (l = 0; l < LANES; l = l + 1)
                    if (result[8*l +: 8] !== ref8(pop, ma[(c-2)*LANES + l], mb[(c-2)*LANES + l])) errors = errors + 1;
                last_cyc = cyc;
            end
            if (c < P) begin
                if (first_cyc < 0) first_cyc = cyc;
                for (l = 0; l < LANES; l = l + 1) begin a_in[8*l +: 8] = ma[c*LANES + l]; b_in[8*l +: 8] = mb[c*LANES + l]; end
            end else begin a_in = 0; b_in = 0; end
            opcode = (c >= 1 && c <= P) ? ((c - 1) % 6) : 3'd0;  // opcode applied while the pass is in the ALU stage
        end
        $display("DLSPERF,%0d,%0d,%0d,%0d,%0d", LANES, N, last_cyc - first_cyc + 1, P, (errors == 0));
        if (errors == 0) $display("DLS PERF RESULT CORRECT (LANES=%0d)", LANES); else $display("DLS PERF RESULT WRONG: %0d errors", errors);
        $finish;
    end
endmodule

// (self-checking: asserts expected vs DUT; nonzero exit on mismatch)
