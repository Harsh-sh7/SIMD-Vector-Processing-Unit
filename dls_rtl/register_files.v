// DLS chips: VECTOR-REGISTER-FILE and RESULT-REGISTER-FILE

// VECTOR-REGISTER-FILE : 2 x LANES 8-Bit-REGISTER_EN  (operand vector A and operand vector B).
// DLS control inputs (confirmed by the design owner): LOAD-A and LOAD-B are write enables of the A / B registers, Clk is the shared clock,
// RESULT_WRITE is the write enable of the RESULT-REGISTER-FILE. (Verilog names: load_a, load_b, clk, result_en.)
module vector_register_file #(
    parameter LANES = 4
) (
    input  wire                 clk,
    input  wire                 load_a, load_b,
    input  wire [8*LANES-1:0]   a_in, b_in,
    output wire [8*LANES-1:0]   a_out, b_out
);
    genvar l;
    generate
        for (l = 0; l < LANES; l = l + 1) begin : g_lane
            register8_en u_a (.clk(clk), .en(load_a), .d(a_in[8*l +: 8]), .q(a_out[8*l +: 8]));
            register8_en u_b (.clk(clk), .en(load_b), .d(b_in[8*l +: 8]), .q(b_out[8*l +: 8]));
        end
    endgenerate
endmodule

// RESULT-REGISTER-FILE : LANES x 8-Bit-REGISTER_EN holding the four lane results
module result_register_file #(
    parameter LANES = 4
) (
    input  wire               clk,
    input  wire               result_en,
    input  wire [8*LANES-1:0] d,
    output wire [8*LANES-1:0] q
);
    genvar l;
    generate
        for (l = 0; l < LANES; l = l + 1) begin : g_lane
            register8_en u_r (.clk(clk), .en(result_en), .d(d[8*l +: 8]), .q(q[8*l +: 8]));
        end
    endgenerate
endmodule
