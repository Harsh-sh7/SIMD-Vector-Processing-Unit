// DLS chip: COMPARE   (1-bit result)  +  1BIT-8BIT (replicates one bit into all 8 bits)
// CONFIRMED by the design owner: COMPARE returns 255 when A == B and 0 otherwise.
// In the DLS chip it is an 8-Bit-SUBTRACTOR followed by an 8-1-ZERO (all-bits-zero detect); A - B == 0 exactly when A == B.
module compare8 (
    input  wire [7:0] a, b,
    output wire       hit
);
    assign hit = (a == b);          // <-- equality, as in the DLS COMPARE chip
endmodule

module bit_to_byte (                 // 1BIT-8BIT
    input  wire       bit_in,
    output wire [7:0] byte_out
);
    assign byte_out = {8{bit_in}};
endmodule
