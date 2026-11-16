// DLS chips: 8-Bit-AND, 8-Bit-OR, 8-Bit-XOR   (collection 8-Bit-OPERATORS; 8 gates side by side)
module and8 (input wire [7:0] a, b, output wire [7:0] y); assign y = a & b; endmodule
module or8  (input wire [7:0] a, b, output wire [7:0] y); assign y = a | b; endmodule
module xor8 (input wire [7:0] a, b, output wire [7:0] y); assign y = a ^ b; endmodule
