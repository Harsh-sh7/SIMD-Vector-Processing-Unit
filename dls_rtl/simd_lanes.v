// DLS chip: SIMD_4LANE  =  VECTOR-REGISTER-FILE -> 4 x 8-Bit-ALU -> RESULT-REGISTER-FILE
// Generalised here to LANES lanes so the same design can be used as the scalar baseline (LANES = 1).
// One shared opcode drives every ALU (Single Instruction, Multiple Data).
//
// Timing (all enables held high = streaming mode): operands captured on edge n, results captured on edge n+1,
// one new operand pair per clock. With the enables pulsed by hand (as in the DLS simulator) it takes
// one clock to load the operands and one more to capture the result.
module simd_lanes #(
    parameter LANES = 4
) (
    input  wire                 clk,
    input  wire                 load_a, load_b,      // enable the operand registers
    input  wire                 result_en,           // enable the result registers
    input  wire [2:0]           opcode,
    input  wire [8*LANES-1:0]   a_in, b_in,          // packed operand vectors (lane 0 = bits 7:0)
    output wire [8*LANES-1:0]   result
);
    wire [8*LANES-1:0] a_q, b_q, alu_out;

    vector_register_file #(.LANES(LANES)) u_vrf (
        .clk(clk), .load_a(load_a), .load_b(load_b),
        .a_in(a_in), .b_in(b_in), .a_out(a_q), .b_out(b_q));

    genvar l;
    generate
        for (l = 0; l < LANES; l = l + 1) begin : g_alu
            alu8 u_alu (.opcode(opcode), .a(a_q[8*l +: 8]), .b(b_q[8*l +: 8]), .y(alu_out[8*l +: 8]));
        end
    endgenerate

    result_register_file #(.LANES(LANES)) u_rrf (.clk(clk), .result_en(result_en), .d(alu_out), .q(result));
endmodule

// The chip exactly as built in Digital Logic Sim: 4 lanes x 8 bit = 32-bit vectors
module simd_4lane (
    input  wire        clk, load_a, load_b, result_en,
    input  wire [2:0]  opcode,
    input  wire [31:0] a_in, b_in,
    output wire [31:0] result
);
    simd_lanes #(.LANES(4)) u_core (.clk(clk), .load_a(load_a), .load_b(load_b), .result_en(result_en),
                                   .opcode(opcode), .a_in(a_in), .b_in(b_in), .result(result));
endmodule
