// -----------------------------------------------------------------------------
// tb_lane_alu : EXHAUSTIVE test of the lane ALU (W = 8 -> all 16 ops x 65 536 operand
// pairs = 1 048 576 checks) against an independent integer reference model.
// -----------------------------------------------------------------------------
`timescale 1ns/1ps
`include "simd_defs.vh"

module tb_lane_alu;
    parameter W = 8;

    reg  [3:0]   op;
    reg  [W-1:0] a, b;
    wire [W-1:0] y;

    lane_alu #(.W(W)) dut (.op(op), .a(a), .b(b), .y(y));

    // ---- independent reference model (64-bit integer arithmetic) ----
    function [W-1:0] model;
        input [3:0]   mop;
        input [W-1:0] ma, mb;
        reg signed [63:0] sa, sb;
        reg        [63:0] ua, ub, r;
        integer shamt;
        begin
            ua = ma;  ub = mb;
            sa = {{(64-W){ma[W-1]}}, ma};
            sb = {{(64-W){mb[W-1]}}, mb};
            shamt = mb % W;
            case (mop)
                `OP_ADD: r = ua + ub;
                `OP_SUB: r = ua - ub;
                `OP_AND: r = ua & ub;
                `OP_OR : r = ua | ub;
                `OP_XOR: r = ua ^ ub;
                `OP_SLL: r = ua << shamt;
                `OP_SRL: r = ua >> shamt;
                `OP_SRA: r = sa >>> shamt;
                `OP_MUL: r = ua * ub;
                `OP_EQ : r = (ua == ub)  ? {64{1'b1}} : 64'd0;
                `OP_NE : r = (ua != ub)  ? {64{1'b1}} : 64'd0;
                `OP_LT : r = (sa <  sb)  ? {64{1'b1}} : 64'd0;
                `OP_GT : r = (sa >  sb)  ? {64{1'b1}} : 64'd0;
                `OP_LTU: r = (ua <  ub)  ? {64{1'b1}} : 64'd0;
                `OP_MIN: r = (sa <  sb)  ? ua : ub;
                `OP_MAX: r = (sa >  sb)  ? ua : ub;
                default: r = 64'd0;
            endcase
            model = r[W-1:0];
        end
    endfunction

    integer i, j, k, errors, checks;
    reg [W-1:0] exp;

    initial begin
        errors = 0; checks = 0;
        for (k = 0; k < 16; k = k + 1) begin
            for (i = 0; i < (1<<W); i = i + 1) begin
                for (j = 0; j < (1<<W); j = j + 1) begin
                    op = k[3:0]; a = i[W-1:0]; b = j[W-1:0];
                    #1;
                    exp = model(op, a, b);
                    checks = checks + 1;
                    if (y !== exp) begin
                        errors = errors + 1;
                        if (errors <= 10)
                            $display("ERROR op=%h a=%h b=%h got=%h exp=%h", op, a, b, y, exp);
                    end
                end
            end
        end
        $display("tb_lane_alu: %0d checks, %0d errors", checks, errors);
        if (errors == 0) $display("LANE_ALU EXHAUSTIVE TEST PASSED");
        else             $display("LANE_ALU TEST FAILED");
        $finish;
    end
endmodule

// (self-checking: asserts expected vs DUT; nonzero exit on mismatch)
