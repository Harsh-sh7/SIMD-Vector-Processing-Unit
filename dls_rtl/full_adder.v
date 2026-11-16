// DLS chip: FULL_ADDER   (collection ADDER_SUBTRACTOR)
module full_adder (
    input  wire a, b, cin,
    output wire sum, cout
);
    assign sum  = a ^ b ^ cin;
    assign cout = (a & b) | (cin & (a ^ b));
endmodule
