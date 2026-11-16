// DLS chip: 8-Bit-RC-ADDER   (8 x FULL_ADDER, carry rippling from bit 0 to bit 7)
module rc_adder8 (
    input  wire [7:0] a, b,
    input  wire       cin,
    output wire [7:0] sum,
    output wire       cout
);
    wire [8:0] c;
    assign c[0] = cin;
    genvar i;
    generate
        for (i = 0; i < 8; i = i + 1) begin : g_fa
            full_adder u_fa (.a(a[i]), .b(b[i]), .cin(c[i]), .sum(sum[i]), .cout(c[i+1]));
        end
    endgenerate
    assign cout = c[8];
endmodule
