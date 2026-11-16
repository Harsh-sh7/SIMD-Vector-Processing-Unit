// DLS chip: 8-Bit-ALU   (one SIMD lane)
//   five operator chips + COMPARE -> 8-1-MUX(8-Bit) selected by a 3-bit opcode
//   opcode (read from the DLS select bulbs):  000 ADD   001 SUB   010 AND   011 OR   100 XOR   101 COMPARE(==)
//   110 and 111 are not connected in the DLS chip (output 0)
module alu8 (
    input  wire [2:0] opcode,
    input  wire [7:0] a, b,
    output wire [7:0] y
);
    wire [7:0] r_add, r_sub, r_and, r_or, r_xor, r_cmp;
    wire       cout, no_borrow, hit;

    rc_adder8   u_add (.a(a), .b(b), .cin(1'b0), .sum(r_add), .cout(cout));
    subtractor8 u_sub (.a(a), .b(b), .diff(r_sub), .no_borrow(no_borrow));
    and8        u_and (.a(a), .b(b), .y(r_and));
    or8         u_or  (.a(a), .b(b), .y(r_or));
    xor8        u_xor (.a(a), .b(b), .y(r_xor));
    compare8    u_cmp (.a(a), .b(b), .hit(hit));
    bit_to_byte u_b2b (.bit_in(hit), .byte_out(r_cmp));

    mux8to1_8bit u_mux (.sel(opcode),
                        .d0(r_add), .d1(r_sub), .d2(r_and), .d3(r_or),
                        .d4(r_xor), .d5(r_cmp), .d6(8'h00), .d7(8'h00), .y(y));
endmodule
