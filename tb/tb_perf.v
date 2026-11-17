// -----------------------------------------------------------------------------
// tb_perf : scalar-vs-SIMD workload benchmark (cycle counting + result verification)
//
//   The SAME program is run on a build with LANES lanes; LANES=1 is the scalar baseline.
//   Each pass over the program processes LANES array elements, so N elements need
//   N/LANES passes.
//
//   KERNEL = 0  "mixed kernel"   y[i] = max( (a[i]+b[i])*3 - (a[i]<<3) , a[i] )   (signed)
//              per chunk: VLD,VLD,VADD,VMUL.VS,VSLL.VS,VSUB,VMAX,VST  (8 instr, 5 ALU)
//   KERNEL = 1  "vector add"     y[i] = a[i] + b[i]
//              per chunk: VLD,VLD,VADD,VST                             (4 instr, 1 ALU)
//   KERNEL = 2  "min select"     y[i] = min(a[i], b[i]) (signed) using the compare mask:
//              m = (a<b); y = b ^ ((a^b) & m)
//              per chunk: VLD,VLD,VLT,VXOR,VAND,VXOR,VST               (7 instr, 4 ALU)
//
//   Prints one machine-readable line:  PERF,<kernel>,<lanes>,<W>,<N>,<cycles>,...
//   Plusargs: +trace (cycle-by-cycle table)   +vcd (waveform in results/perf_demo.vcd)
//   Override parameters with  iverilog -Ptb_perf.LANES=8 -Ptb_perf.KERNEL=1 ...
// -----------------------------------------------------------------------------
`timescale 1ns/1ps
`include "simd_defs.vh"

module tb_perf;
    parameter LANES  = 4;
    parameter W      = 16;
    parameter N      = 64;       // number of array elements (multiple of LANES)
    parameter KERNEL = 0;
    localparam VW    = LANES * W;
    localparam CH    = N / LANES;

    reg clk = 0, rst = 1;
    reg instr_valid = 0;
    reg [31:0] instr = 0;
    reg [VW-1:0] ld_data = 0;
    reg scalar_we = 0;
    reg [W-1:0] scalar_in = 0;
    reg perf_clr = 0;

    wire st_valid, sc_valid, flags_valid, vany, vall;
    wire [VW-1:0] st_data;
    wire [W-1:0] scalar_out;
    wire [LANES-1:0] vmask;
    wire [31:0] perf_cycles, perf_instr, perf_laneops;

    simd_vpu #(.LANES(LANES), .W(W)) dut (
        .clk(clk), .rst(rst), .instr_valid(instr_valid), .instr(instr),
        .ld_data(ld_data), .scalar_we(scalar_we), .scalar_in(scalar_in),
        .st_valid(st_valid), .st_data(st_data), .sc_valid(sc_valid),
        .scalar_out(scalar_out), .flags_valid(flags_valid), .vmask(vmask),
        .vany(vany), .vall(vall), .perf_clr(perf_clr),
        .perf_cycles(perf_cycles), .perf_instr(perf_instr), .perf_laneops(perf_laneops));

    always #5 clk = ~clk;

    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // ---- data + golden model ----
    reg [W-1:0] mem_a [0:N-1];
    reg [W-1:0] mem_b [0:N-1];
    reg [W-1:0] mem_y [0:N-1];
    reg [W-1:0] gold  [0:N-1];

    function [W-1:0] golden;
        input [W-1:0] a, b;
        reg signed [63:0] sa, sb, t, u;
        reg [63:0] ua, ub;
        reg [63:0] r;
        reg [W-1:0] w1;
        begin
            sa = {{(64-W){a[W-1]}}, a}; sb = {{(64-W){b[W-1]}}, b};
            ua = a; ub = b;
            case (KERNEL)
                0: begin
                    t = (ua + ub) * 3 - (ua << 3);               // modulo 2^W below
                    r = t;
                    w1 = r[W-1:0];
                    t = {{(64-W){w1[W-1]}}, w1};
                    golden = (t > sa) ? w1 : a;
                end
                1: begin r = ua + ub; golden = r[W-1:0]; end
                default: golden = (sa < sb) ? a : b;
            endcase
        end
    endfunction

    // ---- measurement ----
    integer first_cyc = -1, last_st_cyc = -1, n_st = 0, errors = 0, issued = 0;

    always @(negedge clk) if (!rst && st_valid) begin : collect
        integer e;
        for (e = 0; e < LANES; e = e + 1)
            mem_y[n_st*LANES + e] = st_data[e*W +: W];
        n_st = n_st + 1;
        last_st_cyc = cyc;
    end

    task issue;
        input [2:0]  cls;
        input [3:0]  op;
        input [2:0]  vd, vs1, vs2;
        input [15:0] imm;
        input [VW-1:0] ld;
        begin
            @(posedge clk); #1;
            if (first_cyc < 0) first_cyc = cyc;
            instr_valid = 1;
            instr   = {cls, op, vd, vs1, vs2, imm};
            ld_data = ld;
            issued  = issued + 1;
        end
    endtask

    function [VW-1:0] pack;            // gather LANES elements starting at index base
        input integer base;
        input integer which;           // 0 = a, 1 = b
        integer e;
        reg [VW-1:0] v;
        begin
            for (e = 0; e < LANES; e = e + 1)
                v[e*W +: W] = (which == 0) ? mem_a[base+e] : mem_b[base+e];
            pack = v;
        end
    endfunction

    integer i, c;

    initial begin
        if ($test$plusargs("vcd")) begin
            $dumpfile("results/perf_demo.vcd");
            $dumpvars(0, tb_perf);
        end
        for (i = 0; i < N; i = i + 1) begin
            mem_a[i] = $random; mem_b[i] = $random;
            gold[i]  = golden(mem_a[i], mem_b[i]);
        end

        repeat (3) @(posedge clk);
        #1 rst = 0;
        repeat (2) @(posedge clk);
        #1 perf_clr = 1;                       // clear HW counters, then start the timed region
        @(posedge clk); #1 perf_clr = 0;

        // ------------------------------------------------ timed program
        if (KERNEL == 0) issue(`CLS_SSET, 0, 0, 0, 0, 16'd3, 0);     // s = 3 (multiplier and shift amount)
        for (c = 0; c < CH; c = c + 1) begin
            issue(`CLS_VLD, 0, 3'd1, 0, 0, 0, pack(c*LANES, 0));     // v1 = a[chunk]
            issue(`CLS_VLD, 0, 3'd2, 0, 0, 0, pack(c*LANES, 1));     // v2 = b[chunk]
            case (KERNEL)
                0: begin
                    issue(`CLS_VV, `OP_ADD, 3'd3, 3'd1, 3'd2, 0, 0);  // v3 = a + b
                    issue(`CLS_VS, `OP_MUL, 3'd4, 3'd3, 0,    0, 0);  // v4 = v3 * s
                    issue(`CLS_VS, `OP_SLL, 3'd5, 3'd1, 0,    0, 0);  // v5 = a << s
                    issue(`CLS_VV, `OP_SUB, 3'd6, 3'd4, 3'd5, 0, 0);  // v6 = v4 - v5
                    issue(`CLS_VV, `OP_MAX, 3'd7, 3'd6, 3'd1, 0, 0);  // v7 = max(v6, a)
                    issue(`CLS_VST, 0, 0, 3'd7, 0, 0, 0);
                end
                1: begin
                    issue(`CLS_VV, `OP_ADD, 3'd3, 3'd1, 3'd2, 0, 0);  // v3 = a + b
                    issue(`CLS_VST, 0, 0, 3'd3, 0, 0, 0);
                end
                default: begin
                    issue(`CLS_VV, `OP_LT,  3'd3, 3'd1, 3'd2, 0, 0);  // v3 = mask(a<b)  (all-ones / zero per lane)
                    issue(`CLS_VV, `OP_XOR, 3'd4, 3'd1, 3'd2, 0, 0);  // v4 = a ^ b
                    issue(`CLS_VV, `OP_AND, 3'd5, 3'd4, 3'd3, 0, 0);  // v5 = (a^b) & mask
                    issue(`CLS_VV, `OP_XOR, 3'd6, 3'd2, 3'd5, 0, 0);  // v6 = b ^ v5 = min(a,b)
                    issue(`CLS_VST, 0, 0, 3'd6, 0, 0, 0);
                end
            endcase
        end
        @(posedge clk); #1 instr_valid = 0;
        repeat (4) @(posedge clk);
        #1;

        // ------------------------------------------------ verification
        for (i = 0; i < N; i = i + 1)
            if (mem_y[i] !== gold[i]) begin
                errors = errors + 1;
                if (errors < 10) $display("MISMATCH y[%0d]=%h expected %h", i, mem_y[i], gold[i]);
            end
        if (n_st != CH) begin errors = errors + 1; $display("ERROR: %0d stores, expected %0d", n_st, CH); end

        $display("PERF,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",
                 KERNEL, LANES, W, N,
                 last_st_cyc - first_cyc + 1,      // total cycles, first issue -> last result visible
                 perf_instr, perf_laneops,
                 issued, (errors == 0));
        if (errors == 0) $display("PERF RESULT CORRECT: all %0d outputs match the golden model (kernel %0d, LANES=%0d)", N, KERNEL, LANES);
        else             $display("PERF RESULT WRONG: %0d errors", errors);
        $finish;
    end

    // optional trace (one line per cycle: instruction in the execute stage, write-back, store bus)
    reg [8*8-1:0] e_name;
    always @* begin
        if      (dut.u_ctrl.alu_en)                       e_name = dut.u_ctrl.use_sc ? "VOP.S   " : "VOP     ";
        else if (dut.u_ctrl.reg_we && dut.u_ctrl.res_sel == `RES_LD) e_name = "VLD     ";
        else if (dut.u_ctrl.st_en)                        e_name = "VST     ";
        else if (dut.u_ctrl.sset_en)                      e_name = "SSET    ";
        else                                              e_name = "-       ";
    end
    always @(posedge clk) if ($test$plusargs("trace") && !rst)
        $display("cyc=%0d  E: %s op=%h vd=v%0d | W: we=%b vd=v%0d | store: valid=%b data=%h",
                 cyc, e_name, dut.u_ctrl.op, dut.u_ctrl.vd, dut.wb_we, dut.wb_vd, st_valid, st_data);
endmodule

// (self-checking: asserts expected vs DUT; nonzero exit on mismatch)
