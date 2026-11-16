// DLS chip: 8-1-MUX(8-Bit)   8 inputs of 8 bits, 3-bit select
module mux8to1_8bit (
    input  wire [2:0] sel,
    input  wire [7:0] d0, d1, d2, d3, d4, d5, d6, d7,
    output reg  [7:0] y
);
    always @* begin
        case (sel)
            3'd0: y = d0;  3'd1: y = d1;  3'd2: y = d2;  3'd3: y = d3;
            3'd4: y = d4;  3'd5: y = d5;  3'd6: y = d6;  default: y = d7;
        endcase
    end
endmodule
