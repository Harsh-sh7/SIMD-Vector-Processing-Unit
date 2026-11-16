// -----------------------------------------------------------------------------
// simd_lane : one lane of the datapath = operand-B lane MUX + lane ALU + result MUX
//   operand B  : vector register lane (VV) or broadcast scalar (VS)
//   result     : ALU output / external load data / broadcast scalar
// -----------------------------------------------------------------------------
`include "simd_defs.vh"

module simd_lane #(
    parameter W = 16
) (
    input  wire [3:0]   op,
    input  wire         use_sc,     // 1: operand B = scalar broadcast
    input  wire [1:0]   res_sel,    // RES_ALU / RES_LD / RES_SPL
    input  wire [W-1:0] a,          // vs1 lane
    input  wire [W-1:0] b_vec,      // vs2 lane
    input  wire [W-1:0] sc,         // scalar register (broadcast)
    input  wire [W-1:0] ld,         // external load-bus lane
    output wire [W-1:0] y
);
    wire [W-1:0] b = use_sc ? sc : b_vec;     // lane operand MUX
    wire [W-1:0] alu_y;

    lane_alu #(.W(W)) u_alu (.op(op), .a(a), .b(b), .y(alu_y));

    assign y = (res_sel == `RES_LD)  ? ld    :     // result MUX
               (res_sel == `RES_SPL) ? sc    :
                                       alu_y;
endmodule

// (reviewed: port widths / params consistent with simd_defs.vh)
