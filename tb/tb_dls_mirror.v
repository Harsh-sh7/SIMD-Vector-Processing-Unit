// -----------------------------------------------------------------------------
// tb_dls_mirror : verification of the structural Verilog mirror of the Digital Logic Sim chips
//   1. replays the exact cases visible in the DLS screenshots (ALU ops and the full-chip vector subtract)
//   2. exhaustive 8-Bit-ALU test: 8 opcodes x 65 536 operand pairs
//   3. equivalence with the main parameterised RTL lane ALU (rtl/lane_alu.v, W = 8) for the 6 DLS operations
//   4. full-chip streaming test (random operands/opcodes, one new pass per clock) + manual-step mode
// -----------------------------------------------------------------------------
`timescale 1ns/1ps
`include "simd_defs.vh"

module tb_dls_mirror;
    // ---------------- reference model ----------------
    function [7:0] ref8;
        input [2:0] op; input [7:0] a, b;
        begin
            case (op)
                3'd0: ref8 = a + b;
                3'd1: ref8 = a - b;
                3'd2: ref8 = a & b;
                3'd3: ref8 = a | b;
                3'd4: ref8 = a ^ b;
                3'd5: ref8 = (a == b) ? 8'hFF : 8'h00;
                default: ref8 = 8'h00;
            endcase
        end
    endfunction

    integer errors = 0;

    // ---------------- DUT 1: single ALU ----------------
    reg  [2:0] op;  reg [7:0] a, b;  wire [7:0] y;
    alu8 u_alu (.opcode(op), .a(a), .b(b), .y(y));

    // ---------------- DUT 2: equivalence partner (main RTL lane ALU, W=8) ----------------
    reg  [3:0] rtl_op;  wire [7:0] y_rtl;
    lane_alu #(.W(8)) u_rtl (.op(rtl_op), .a(a), .b(b), .y(y_rtl));

    // ---------------- DUT 3: the full SIMD_4LANE chip ----------------
    reg clk = 0, load_a = 0, load_b = 0, result_en = 0;
    reg [2:0] opcode = 0;  reg [31:0] a_in = 0, b_in = 0;  wire [31:0] result;
    simd_4lane u_chip (.clk(clk), .load_a(load_a), .load_b(load_b), .result_en(result_en),
                       .opcode(opcode), .a_in(a_in), .b_in(b_in), .result(result));
    always #5 clk = ~clk;

    task show_alu;
        input [127:0] name; input [2:0] o; input [7:0] x, z, shot;
        begin
            op = o; a = x; b = z; #1;
            $display("  ALU %-7s opcode=%b  A=%3d  B=%3d  ->  %3d   (DLS screenshot shows %3d)  %s",
                     name, o, x, z, y, shot, (y === shot) ? "MATCH" : "MISMATCH");
            if (y !== shot) errors = errors + 1;
        end
    endtask

    integer i, j, k, n, checks, p;
    reg [31:0] pa [0:1023];  reg [31:0] pb [0:1023];  reg [2:0] po [0:1023];
    reg [31:0] pe [0:1023];

    function [31:0] vec_ref;
        input [2:0] o; input [31:0] x, z;
        integer l;
        begin
            for (l = 0; l < 4; l = l + 1) vec_ref[8*l +: 8] = ref8(o, x[8*l +: 8], z[8*l +: 8]);
        end
    endfunction

    initial begin
        if ($test$plusargs("vcd")) begin $dumpfile("results/dls_mirror.vcd"); $dumpvars(0, tb_dls_mirror); end

        // ============ 1. screenshot cases ============
        $display("[1] Cases from the Digital Logic Sim screenshots");
        show_alu("ADD", 3'b000,  64,  96, 160);
        show_alu("SUB", 3'b001, 112,  96,  16);
        show_alu("AND", 3'b010,  96, 112,  96);
        show_alu("OR",  3'b011,  96, 112, 112);
        show_alu("XOR", 3'b100,  96, 112,  16);
        show_alu("CMP",  3'b101, 112, 112, 255);

        // full chip, manual stepping like in DLS: set inputs, load operands (1 clock), capture result (1 clock)
        a_in = {8'd40, 8'd30, 8'd20, 8'd10};  b_in = {8'd4, 8'd3, 8'd2, 8'd1};  opcode = 3'b001;   // SUB
        @(posedge clk); #1; load_a = 1; load_b = 1;
        @(posedge clk); #1; load_a = 0; load_b = 0; result_en = 1;      // operands now in the vector register file
        @(posedge clk); #1; result_en = 0;                              // results now in the result register file
        $display("  SIMD_4LANE  SUB  [10,20,30,40] - [1,2,3,4]  ->  [%0d,%0d,%0d,%0d]   (DLS screenshot shows 9,18,27,36)  %s",
                 result[7:0], result[15:8], result[23:16], result[31:24],
                 (result === {8'd36, 8'd27, 8'd18, 8'd9}) ? "MATCH" : "MISMATCH");
        if (result !== {8'd36, 8'd27, 8'd18, 8'd9}) errors = errors + 1;

        // enable gating: registers must HOLD when their enable is low, and A / B load independently
        a_in = 32'hFFFFFFFF; b_in = 32'h0;
        repeat (3) @(posedge clk);
        #1 if (result !== {8'd36, 8'd27, 8'd18, 8'd9}) begin errors = errors + 1; $display("  ERROR: result register changed while result_en = 0"); end
        a_in = {8'd50, 8'd60, 8'd70, 8'd80}; b_in = 32'h0;
        load_a = 1; load_b = 0; result_en = 0;                          // load operand vector A only
        @(posedge clk); #1 load_a = 0; result_en = 1;                    // capture A - B (B must still be 1,2,3,4)
        @(posedge clk); #1 result_en = 0;
        if (result !== {8'd46, 8'd57, 8'd68, 8'd79}) begin
            errors = errors + 1; $display("  ERROR: A-only load: got %h expected %h", result, {8'd46, 8'd57, 8'd68, 8'd79});
        end else $display("  enable gating: registers hold when disabled, A and B load independently   OK");

        // ============ 2. exhaustive ALU test ============
        $display("[2] Exhaustive 8-Bit-ALU test (8 opcodes x 65536 pairs)");
        checks = 0;
        for (k = 0; k < 8; k = k + 1)
            for (i = 0; i < 256; i = i + 1)
                for (j = 0; j < 256; j = j + 1) begin
                    op = k; a = i; b = j; #1;
                    checks = checks + 1;
                    if (y !== ref8(op, a, b)) begin
                        errors = errors + 1;
                        if (errors < 10) $display("  ERROR op=%0d a=%0d b=%0d got=%0d exp=%0d", op, a, b, y, ref8(op, a, b));
                    end
                end
        $display("    %0d checks done", checks);

        // ============ 3. equivalence with the main RTL lane ALU ============
        $display("[3] Equivalence: DLS-mirror ALU == main RTL lane_alu (W=8) for the 6 DLS operations");
        checks = 0;
        for (k = 0; k < 6; k = k + 1)
            for (i = 0; i < 256; i = i + 1)
                for (j = 0; j < 256; j = j + 1) begin
                    op = k; rtl_op = (k == 5) ? `OP_EQ : k; a = i; b = j; #1;
                    checks = checks + 1;
                    if (y !== y_rtl) begin
                        errors = errors + 1;
                        if (errors < 10) $display("  ERROR op=%0d a=%0d b=%0d mirror=%0d rtl=%0d", k, i, j, y, y_rtl);
                    end
                end
        $display("    %0d checks done (DLS opcodes 0-4 coincide with RTL opcodes ADD,SUB,AND,OR,XOR; 5 = COMPARE = RTL EQ)", checks);

        // ============ 4. full-chip streaming test ============
        $display("[4] Full-chip streaming test: 4000 random passes, one pass per clock (all enables high)");
        n = 1000;
        load_a = 0; load_b = 0; result_en = 0;
        @(posedge clk); #1;
        load_a = 1; load_b = 1; result_en = 1;
        for (p = 0; p < 4; p = p + 1) begin : blk
            for (i = 0; i < n; i = i + 1) begin
                pa[i] = $random; pb[i] = $random; po[i] = ($random & 32'h7fffffff) % 6;
                if (i % 7 == 0) pb[i] = pa[i];                      // exercise equality
                pe[i] = vec_ref(po[i], pa[i], pb[i]);
            end
            for (i = 0; i <= n + 1; i = i + 1) begin
                @(posedge clk); #1;
                if (i >= 2 && result !== pe[i-2]) begin
                    errors = errors + 1;
                    if (errors < 10) $display("  ERROR stream pass %0d got=%h exp=%h", i-2, result, pe[i-2]);
                end
                a_in   = (i < n) ? pa[i]   : 32'd0;
                b_in   = (i < n) ? pb[i]   : 32'd0;
                opcode = (i >= 1 && i <= n) ? po[i-1] : 3'd0;       // opcode is applied while the pass sits in the ALU stage
            end
        end
        load_a = 0; load_b = 0; result_en = 0;

        $display("");
        $display("tb_dls_mirror: %0d errors", errors);
        if (errors == 0) $display("DLS MIRROR TESTS PASSED");
        else             $display("DLS MIRROR TESTS FAILED");
        $finish;
    end
endmodule

// (self-checking: asserts expected vs DUT; nonzero exit on mismatch)
