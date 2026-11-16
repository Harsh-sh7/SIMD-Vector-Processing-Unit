// -----------------------------------------------------------------------------
// lane_alu : one W-bit ALU. The SIMD unit instantiates LANES copies of this.
// Compare operations return an all-ones (true) or all-zero (false) lane mask,
// which is the usual SIMD convention and can be used directly as an AND mask.
// -----------------------------------------------------------------------------
`include "simd_defs.vh"

module lane_alu #(
    parameter W = 16
) (
    input  wire [3:0]   op,
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    output reg  [W-1:0] y
);
    function integer clog2;
        input integer v;
        integer i;
        begin
            clog2 = 0;
            for (i = 1; i < v; i = i << 1) clog2 = clog2 + 1;
        end
    endfunction

    localparam SHW = (W > 1) ? clog2(W) : 1;     // shift-amount width

    wire signed [W-1:0] sa = a;
    wire signed [W-1:0] sb = b;
    wire [SHW-1:0]      sh = b[SHW-1:0];

    wire eq  = (a == b);
    wire lt  = (sa <  sb);
    wire gt  = (sa >  sb);
    wire ltu = (a  <  b);

    always @* begin
        case (op)
            `OP_ADD: y = a + b;
            `OP_SUB: y = a - b;
            `OP_AND: y = a & b;
            `OP_OR : y = a | b;
            `OP_XOR: y = a ^ b;
            `OP_SLL: y = a << sh;
            `OP_SRL: y = a >> sh;
            `OP_SRA: y = sa >>> sh;
            `OP_MUL: y = a * b;
            `OP_EQ : y = {W{eq}};
            `OP_NE : y = {W{~eq}};
            `OP_LT : y = {W{lt}};
            `OP_GT : y = {W{gt}};
            `OP_LTU: y = {W{ltu}};
            `OP_MIN: y = lt ? a : b;
            `OP_MAX: y = gt ? a : b;
            default: y = {W{1'b0}};
        endcase
    end
endmodule

// (reviewed: port widths / params consistent with simd_defs.vh)
