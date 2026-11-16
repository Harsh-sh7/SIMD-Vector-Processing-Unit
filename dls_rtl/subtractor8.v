// DLS chip: 8-Bit-SUBTRACTOR   a - b = a + ~b + 1 (two's complement) built from the RC adder
module subtractor8 (
    input  wire [7:0] a, b,
    output wire [7:0] diff,
    output wire       no_borrow       // carry out of the adder: 1 when a >= b (unsigned)
);
    rc_adder8 u_add (.a(a), .b(~b), .cin(1'b1), .sum(diff), .cout(no_borrow));
endmodule
