// DLS chip: COMPARE   (1-bit result)  +  1BIT-8BIT (replicates one bit into all 8 bits)
// ASSUMPTION: COMPARE is an equality compare (screenshot: 112 vs 112 -> 255).
// If your DLS COMPARE is a different relation (e.g. A >= B), change the one line marked below.
module compare8 (
    input  wire [7:0] a, b,
    output wire       hit
);
    assign hit = (a == b);          // <-- relation implemented by the DLS COMPARE chip
endmodule

module bit_to_byte (                 // 1BIT-8BIT
    input  wire       bit_in,
    output wire [7:0] byte_out
);
    assign byte_out = {8{bit_in}};
endmodule
