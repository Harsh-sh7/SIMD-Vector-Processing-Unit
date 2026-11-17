// -----------------------------------------------------------------------------
// tb_vectors : replays the golden vector file produced by scripts/gen_dls_vectors.py through the
// RTL (VLD, VLD, VV-op, VST sequence) and checks every lane. The same file is used to cross-check
// the Digital Logic Sim SIMD_4LANE implementation, so RTL == Python model == DLS chip.
//   iverilog -Ptb_vectors.LANES=4 -Ptb_vectors.W=8 -Ptb_vectors.FILE=\"vectors/vectors_L4_W8.mem\" ...
// -----------------------------------------------------------------------------
`timescale 1ns/1ps
`include "simd_defs.vh"

module tb_vectors;
    parameter LANES = 4;
    parameter W     = 8;
    parameter NVEC  = 192;
    parameter FILE  = "vectors/vectors_L4_W8.mem";
    localparam VW   = LANES * W;

    reg clk = 0, rst = 1, instr_valid = 0;
    reg [31:0] instr = 0;
    reg [VW-1:0] ld_data = 0;
    wire st_valid, sc_valid, flags_valid, vany, vall;
    wire [VW-1:0] st_data;
    wire [W-1:0] scalar_out;
    wire [LANES-1:0] vmask;
    wire [31:0] pc, pi, pl;

    simd_vpu #(.LANES(LANES), .W(W)) dut (
        .clk(clk), .rst(rst), .instr_valid(instr_valid), .instr(instr), .ld_data(ld_data),
        .scalar_we(1'b0), .scalar_in({W{1'b0}}), .st_valid(st_valid), .st_data(st_data),
        .sc_valid(sc_valid), .scalar_out(scalar_out), .flags_valid(flags_valid), .vmask(vmask),
        .vany(vany), .vall(vall), .perf_clr(1'b0), .perf_cycles(pc), .perf_instr(pi), .perf_laneops(pl));

    always #5 clk = ~clk;

    reg [VW-1:0] mem [0:4*NVEC-1];
    integer t, errors = 0, checked = 0;
    reg [VW-1:0] exp_q [0:NVEC-1];
    integer rd_i = 0;

    always @(negedge clk) if (!rst && st_valid) begin
        if (st_data !== exp_q[rd_i]) begin
            errors = errors + 1;
            $display("MISMATCH vector %0d: got %h expected %h", rd_i, st_data, exp_q[rd_i]);
        end
        rd_i = rd_i + 1; checked = checked + 1;
    end

    task issue;
        input [2:0] cls; input [3:0] op; input [2:0] vd, vs1, vs2; input [VW-1:0] ld;
        begin
            @(posedge clk); #1;
            instr_valid = 1; instr = {cls, op, vd, vs1, vs2, 16'd0}; ld_data = ld;
        end
    endtask

    integer nv;
    initial begin
        $readmemh(FILE, mem);
        nv = 0;
        while (nv < NVEC && mem[4*nv] !== {VW{1'bx}}) nv = nv + 1;
        repeat (3) @(posedge clk);
        #1 rst = 0;
        repeat (2) @(posedge clk);
        for (t = 0; t < nv; t = t + 1) begin
            exp_q[t] = mem[4*t+3];
            issue(`CLS_VLD, 0, 3'd1, 0, 0, mem[4*t+1]);
            issue(`CLS_VLD, 0, 3'd2, 0, 0, mem[4*t+2]);
            issue(`CLS_VV, mem[4*t][3:0], 3'd3, 3'd1, 3'd2, 0);
            issue(`CLS_VST, 0, 0, 3'd3, 0, 0);
        end
        @(posedge clk); #1 instr_valid = 0;
        repeat (5) @(posedge clk);
        $display("tb_vectors: %0d vectors replayed, %0d checked, %0d errors", nv, checked, errors);
        if (errors == 0 && checked == nv && nv > 0) $display("VECTOR REPLAY PASSED (LANES=%0d, W=%0d)", LANES, W);
        else $display("VECTOR REPLAY FAILED");
        $finish;
    end
endmodule

// (self-checking: asserts expected vs DUT; nonzero exit on mismatch)
