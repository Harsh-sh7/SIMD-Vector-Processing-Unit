// DLS chips: D-FLIP-FLOP-EN and 8-Bit-REGISTER_EN  (collection REGISTER-COMPONENTS)

// D-FLIP-FLOP-EN : edge-triggered D flip-flop with write enable
module dff_en (
    input  wire clk, en, d,
    output reg  q
);
    initial q = 1'b0;
    always @(posedge clk) if (en) q <= d;
endmodule

// 8-Bit-REGISTER_EN : 8-1BIT splitter -> 8 x D-FLIP-FLOP-EN -> 1-8BIT merger
module register8_en (
    input  wire       clk, en,
    input  wire [7:0] d,
    output wire [7:0] q
);
    genvar i;
    generate
        for (i = 0; i < 8; i = i + 1) begin : g_bit
            dff_en u_ff (.clk(clk), .en(en), .d(d[i]), .q(q[i]));
        end
    endgenerate
endmodule
