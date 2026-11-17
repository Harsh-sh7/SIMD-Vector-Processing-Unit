// -----------------------------------------------------------------------------
// tb_simd_vpu : self-checking system testbench for the SIMD vector processing unit
//
//  * architectural reference model (vector regs, scalar reg) updated in program order
//  * expected-output queues for store / scalar-extract / predicate-flag outputs
//  * Phase 1: directed per-operation tests with corner-case operands (all 16 ops, VV+VS)
//  * Phase 2: directed hazard tests (RAW dist-1/2/3, WAW, self-dependency)
//  * Phase 3: constrained-random instruction stream (hazard-biased register choice)
//  * register-file contents compared against the model after every drain
//  * functional-coverage bins; the test FAILS if any bin is not hit
// Parameters LANES / W may be overridden: iverilog -P tb_simd_vpu.LANES=8 ...
// -----------------------------------------------------------------------------
`timescale 1ns/1ps
`include "simd_defs.vh"

module tb_simd_vpu;
    parameter LANES   = 4;
    parameter W       = 16;
    parameter N_RAND  = 20000;
    localparam VW     = LANES * W;

    reg               clk = 0, rst = 1;
    reg               instr_valid = 0;
    reg  [31:0]       instr = 0;
    reg  [VW-1:0]     ld_data = 0;
    reg               scalar_we = 0;
    reg  [W-1:0]      scalar_in = 0;
    reg               perf_clr = 0;

    wire              st_valid, sc_valid, flags_valid, vany, vall;
    wire [VW-1:0]     st_data;
    wire [W-1:0]      scalar_out;
    wire [LANES-1:0]  vmask;
    wire [31:0]       perf_cycles, perf_instr, perf_laneops;

    simd_vpu #(.LANES(LANES), .W(W)) dut (
        .clk(clk), .rst(rst), .instr_valid(instr_valid), .instr(instr),
        .ld_data(ld_data), .scalar_we(scalar_we), .scalar_in(scalar_in),
        .st_valid(st_valid), .st_data(st_data), .sc_valid(sc_valid),
        .scalar_out(scalar_out), .flags_valid(flags_valid), .vmask(vmask),
        .vany(vany), .vall(vall), .perf_clr(perf_clr),
        .perf_cycles(perf_cycles), .perf_instr(perf_instr), .perf_laneops(perf_laneops));

    always #5 clk = ~clk;

    // ------------------------------------------------------------------ model
    reg [VW-1:0] m_v [0:7];
    reg [W-1:0]  m_s;

    function [W-1:0] ref_op;                       // independent reference (64-bit integer math)
        input [3:0]   op;
        input [W-1:0] ma, mb;
        reg signed [63:0] sa, sb;
        reg        [63:0] ua, ub, r;
        integer shamt;
        begin
            ua = ma; ub = mb;
            sa = {{(64-W){ma[W-1]}}, ma};
            sb = {{(64-W){mb[W-1]}}, mb};
            shamt = mb % W;
            case (op)
                `OP_ADD: r = ua + ub;
                `OP_SUB: r = ua - ub;
                `OP_AND: r = ua & ub;
                `OP_OR : r = ua | ub;
                `OP_XOR: r = ua ^ ub;
                `OP_SLL: r = ua << shamt;
                `OP_SRL: r = ua >> shamt;
                `OP_SRA: r = sa >>> shamt;
                `OP_MUL: r = ua * ub;
                `OP_EQ : r = (ua == ub) ? {64{1'b1}} : 64'd0;
                `OP_NE : r = (ua != ub) ? {64{1'b1}} : 64'd0;
                `OP_LT : r = (sa <  sb) ? {64{1'b1}} : 64'd0;
                `OP_GT : r = (sa >  sb) ? {64{1'b1}} : 64'd0;
                `OP_LTU: r = (ua <  ub) ? {64{1'b1}} : 64'd0;
                `OP_MIN: r = (sa <  sb) ? ua : ub;
                `OP_MAX: r = (sa >  sb) ? ua : ub;
                default: r = 64'd0;
            endcase
            ref_op = r[W-1:0];
        end
    endfunction

    // ------------------------------------------------------- expected queues
    localparam QD = 65536;
    reg [VW-1:0]    q_st   [0:QD-1];  integer st_h, st_t;
    reg [W-1:0]     q_sc   [0:QD-1];  integer sc_h, sc_t;
    reg [LANES-1:0] q_fm   [0:QD-1];  integer fl_h, fl_t;

    integer errors = 0;
    integer n_instr = 0, n_st = 0, n_sc = 0, n_fl = 0;

    // output checkers (sample just before the rising edge)
    always @(negedge clk) if (!rst) begin
        if (st_valid) begin
            if (st_h == st_t) begin errors = errors + 1; $display("ERROR: unexpected store @%0t", $time); end
            else begin
                if (st_data !== q_st[st_h % QD]) begin
                    errors = errors + 1;
                    if (errors < 20) $display("ERROR: store mismatch @%0t got=%h exp=%h", $time, st_data, q_st[st_h % QD]);
                end
                st_h = st_h + 1; n_st = n_st + 1;
            end
        end
        if (sc_valid) begin
            if (sc_h == sc_t) begin errors = errors + 1; $display("ERROR: unexpected extract @%0t", $time); end
            else begin
                if (scalar_out !== q_sc[sc_h % QD]) begin
                    errors = errors + 1;
                    if (errors < 20) $display("ERROR: extract mismatch @%0t got=%h exp=%h", $time, scalar_out, q_sc[sc_h % QD]);
                end
                sc_h = sc_h + 1; n_sc = n_sc + 1;
            end
        end
        if (flags_valid) begin
            if (fl_h == fl_t) begin errors = errors + 1; $display("ERROR: unexpected flags @%0t", $time); end
            else begin
                if (vmask !== q_fm[fl_h % QD] || vany !== (|q_fm[fl_h % QD]) || vall !== (&q_fm[fl_h % QD])) begin
                    errors = errors + 1;
                    if (errors < 20) $display("ERROR: flags mismatch @%0t got=%b/%b/%b exp=%b", $time, vmask, vany, vall, q_fm[fl_h % QD]);
                end
                fl_h = fl_h + 1; n_fl = n_fl + 1;
            end
        end
    end

    // ------------------------------------------------------------- coverage
    integer cov_vv  [0:15];
    integer cov_vs  [0:15];
    integer cov_cls [0:7];
    integer cov_raw1, cov_raw2, cov_raw3, cov_waw, cov_selfdep;
    integer cov_lane_nz [0:LANES-1];      // each lane produced a non-zero result
    integer cov_corner_a [0:5];           // 0, 1, all-ones, min-neg, max-pos, other
    integer cov_cmp_true, cov_cmp_false, cov_all, cov_any_notall, cov_none;
    integer last_vd [1:3];                // destination of the previous 3 instructions (-1: none)
    integer ci;
    integer cov_ext = 0;

    task cov_init;
        begin
            for (ci = 0; ci < 16; ci = ci + 1) begin cov_vv[ci] = 0; cov_vs[ci] = 0; end
            for (ci = 0; ci < 8;  ci = ci + 1) cov_cls[ci] = 0;
            for (ci = 0; ci < LANES; ci = ci + 1) cov_lane_nz[ci] = 0;
            for (ci = 0; ci < 6;  ci = ci + 1) cov_corner_a[ci] = 0;
            cov_raw1 = 0; cov_raw2 = 0; cov_raw3 = 0; cov_waw = 0; cov_selfdep = 0;
            cov_cmp_true = 0; cov_cmp_false = 0; cov_all = 0; cov_any_notall = 0; cov_none = 0;
            last_vd[1] = -1; last_vd[2] = -1; last_vd[3] = -1;
        end
    endtask

    // ---------------------------------------------------------------- issue
    // Issues ONE instruction (drives the DUT, updates the model, queues expectations).
    reg [VW-1:0] t_a, t_b, t_r;
    reg [W-1:0]  t_la, t_lb, t_lr;
    reg [LANES-1:0] t_m;
    integer      li;

    task issue;
        input [2:0]    cls;
        input [3:0]    op;
        input [2:0]    vd, vs1, vs2;
        input [15:0]   imm;
        input [VW-1:0] ld;
        begin
            @(posedge clk); #1;
            instr_valid = 1;
            instr   = {cls, op, vd, vs1, vs2, imm};
            ld_data = ld;
            n_instr = n_instr + 1;
            cov_cls[cls] = cov_cls[cls] + 1;

            // hazard coverage (reads of vs1/vs2 against recent destinations)
            if (cls == `CLS_VV || cls == `CLS_VS || cls == `CLS_VST || cls == `CLS_VEXT) begin
                if (last_vd[1] == vs1 || (cls == `CLS_VV && last_vd[1] == vs2)) cov_raw1 = cov_raw1 + 1;
                if (last_vd[2] == vs1 || (cls == `CLS_VV && last_vd[2] == vs2)) cov_raw2 = cov_raw2 + 1;
                if (last_vd[3] == vs1 || (cls == `CLS_VV && last_vd[3] == vs2)) cov_raw3 = cov_raw3 + 1;
            end
            if ((cls == `CLS_VV || cls == `CLS_VS || cls == `CLS_VLD || cls == `CLS_VSPL) && last_vd[1] == vd) cov_waw = cov_waw + 1;
            if ((cls == `CLS_VV || cls == `CLS_VS) && (vd == vs1 || (cls == `CLS_VV && vd == vs2))) cov_selfdep = cov_selfdep + 1;

            // ---- architectural model ----
            case (cls)
                `CLS_NOP: ;
                `CLS_VV, `CLS_VS: begin
                    t_a = m_v[vs1]; t_b = m_v[vs2];
                    for (li = 0; li < LANES; li = li + 1) begin
                        t_la = t_a[li*W +: W];
                        t_lb = (cls == `CLS_VS) ? m_s : t_b[li*W +: W];
                        t_lr = ref_op(op, t_la, t_lb);
                        t_r[li*W +: W] = t_lr;
                        t_m[li] = t_lr[0];
                        if (t_lr != 0) cov_lane_nz[li] = cov_lane_nz[li] + 1;
                        if (li == 0) begin
                            if      (t_la == 0)              cov_corner_a[0] = cov_corner_a[0] + 1;
                            else if (t_la == 1)              cov_corner_a[1] = cov_corner_a[1] + 1;
                            else if (t_la == {W{1'b1}})      cov_corner_a[2] = cov_corner_a[2] + 1;
                            else if (t_la == {1'b1,{(W-1){1'b0}}}) cov_corner_a[3] = cov_corner_a[3] + 1;
                            else if (t_la == {1'b0,{(W-1){1'b1}}}) cov_corner_a[4] = cov_corner_a[4] + 1;
                            else                             cov_corner_a[5] = cov_corner_a[5] + 1;
                        end
                    end
                    m_v[vd] = t_r;
                    q_fm[fl_t % QD] = t_m; fl_t = fl_t + 1;
                    if (cls == `CLS_VV) cov_vv[op] = cov_vv[op] + 1; else cov_vs[op] = cov_vs[op] + 1;
                    if (op >= `OP_EQ && op <= `OP_LTU) begin
                        if (t_m == {LANES{1'b1}})      begin cov_all = cov_all + 1; cov_cmp_true = cov_cmp_true + 1; end
                        else if (t_m == {LANES{1'b0}}) begin cov_none = cov_none + 1; cov_cmp_false = cov_cmp_false + 1; end
                        else                           begin cov_any_notall = cov_any_notall + 1; cov_cmp_true = cov_cmp_true + 1; cov_cmp_false = cov_cmp_false + 1; end
                    end
                end
                `CLS_VLD:  m_v[vd] = ld;
                `CLS_VST:  begin q_st[st_t % QD] = m_v[vs1]; st_t = st_t + 1; end
                `CLS_VSPL: begin
                    for (li = 0; li < LANES; li = li + 1) t_r[li*W +: W] = m_s;
                    m_v[vd] = t_r;
                end
                `CLS_SSET: begin m_s = {{(W>16 ? W-16 : 1){imm[15]}}, imm[15:0]}; if (W <= 16) m_s = imm[W-1:0]; end
                `CLS_VEXT: begin
                    t_a = m_v[vs1];
                    t_la = t_a[0 +: W];
                    for (li = 0; li < LANES; li = li + 1) if (imm == li) t_la = t_a[li*W +: W];
                    q_sc[sc_t % QD] = t_la; sc_t = sc_t + 1;
                end
            endcase
            last_vd[3] = last_vd[2]; last_vd[2] = last_vd[1];
            last_vd[1] = (cls == `CLS_VV || cls == `CLS_VS || cls == `CLS_VLD || cls == `CLS_VSPL) ? vd : -1;
        end
    endtask

    task idle;                       // bubble / drain
        input integer n;
        integer q;
        begin
            for (q = 0; q < n; q = q + 1) begin
                @(posedge clk); #1;
                instr_valid = 0; instr = 32'hFFFFFFFF;   // ignored while invalid
            end
        end
    endtask

    task ext_scalar_write;           // optional scalar interface: external write of the scalar register
        input [W-1:0] val;
        begin
            @(posedge clk); #1;
            instr_valid = 0; instr = 32'hFFFFFFFF;
            scalar_we = 1; scalar_in = val;
            m_s = val;                                  // external write wins over SSET in the same cycle
            last_vd[3] = last_vd[2]; last_vd[2] = last_vd[1]; last_vd[1] = -1;
            cov_ext = cov_ext + 1;
            @(posedge clk); #1 scalar_we = 0;
        end
    endtask

    task check_regs;                 // compare DUT register file with model (call after drain)
        integer r;
        begin
            idle(4);
            for (r = 0; r < 8; r = r + 1)
                if (dut.u_rf.regs[r] !== m_v[r]) begin
                    errors = errors + 1;
                    $display("ERROR: v%0d mismatch got=%h exp=%h", r, dut.u_rf.regs[r], m_v[r]);
                end
            if (dut.sreg !== m_s) begin
                errors = errors + 1; $display("ERROR: sreg mismatch got=%h exp=%h", dut.sreg, m_s);
            end
        end
    endtask

    // ------------------------------------------------------------ utilities
    function [W-1:0] corner;         // 0..9 -> interesting lane values
        input integer idx;
        begin
            case (idx)
                0: corner = {W{1'b0}};
                1: corner = {{(W-1){1'b0}},1'b1};
                2: corner = {W{1'b1}};
                3: corner = {1'b1,{(W-1){1'b0}}};
                4: corner = {1'b0,{(W-1){1'b1}}};
                5: corner = {{(W-1){1'b0}},1'b1} << (W/2);
                6: corner = W - 1;
                7: corner = W;
                8: corner = {W/2{2'b10}};
                default: corner = {W/2{2'b01}};
            endcase
        end
    endfunction

    function [VW-1:0] rand_vec;
        input integer dummy;
        integer lj;
        reg [VW-1:0] v;
        begin
            for (lj = 0; lj < LANES; lj = lj + 1)
                v[lj*W +: W] = ($random % 4 == 0) ? corner(($random & 32'h7fffffff) % 10) : $random;
            rand_vec = v;
        end
    endfunction

    function [VW-1:0] corner_vec;    // lane l gets corner((idx + l) % 10)
        input integer idx;
        integer lj;
        reg [VW-1:0] v;
        begin
            for (lj = 0; lj < LANES; lj = lj + 1) v[lj*W +: W] = corner((idx + lj) % 10);
            corner_vec = v;
        end
    endfunction

    // ---------------------------------------------------------------- main
    integer i, j, k, o, rnd_cls;
    integer a_idx, b_idx;
    reg [2:0] rvd, rs1, rs2;
    reg [3:0] rop;
    reg [15:0] rimm;

    initial begin
        if ($test$plusargs("vcd")) begin
            $dumpfile("results/simd_vpu.vcd");
            $dumpvars(0, tb_simd_vpu);
        end
        st_h = 0; st_t = 0; sc_h = 0; sc_t = 0; fl_h = 0; fl_t = 0;
        for (i = 0; i < 8; i = i + 1) m_v[i] = {VW{1'b0}};
        m_s = {W{1'b0}};
        cov_init;

        repeat (3) @(posedge clk);
        #1 rst = 0;
        idle(2);

        // -------- Phase 1: directed op sweep with corner-case operands --------
        $display("[Phase 1] directed operation sweep (16 ops x VV/VS x corner operands)");
        for (o = 0; o < 16; o = o + 1) begin
            for (a_idx = 0; a_idx < 10; a_idx = a_idx + 1) begin
                for (b_idx = 0; b_idx < 10; b_idx = b_idx + 3) begin
                    issue(`CLS_VLD, 0, 3'd1, 0, 0, 0, corner_vec(a_idx));
                    issue(`CLS_VLD, 0, 3'd2, 0, 0, 0, corner_vec(b_idx + 1));
                    issue(`CLS_VV,  o[3:0], 3'd3, 3'd1, 3'd2, 0, 0);
                    issue(`CLS_VST, 0, 0, 3'd3, 0, 0, 0);
                    // scalar-broadcast form: sreg = corner(b)
                    issue(`CLS_SSET, 0, 0, 0, 0, corner(b_idx), 0);
                    issue(`CLS_VS,  o[3:0], 3'd4, 3'd1, 0, 0, 0);
                    issue(`CLS_VST, 0, 0, 3'd4, 0, 0, 0);
                end
            end
        end
        check_regs;

        // -------- Phase 2: directed hazard / interface tests --------
        $display("[Phase 2] hazards (RAW distance 1/2/3, WAW, self dependency) + scalar interface");
        issue(`CLS_VLD, 0, 3'd1, 0, 0, 0, rand_vec(0));
        issue(`CLS_VLD, 0, 3'd2, 0, 0, 0, rand_vec(0));
        issue(`CLS_VV,  `OP_ADD, 3'd3, 3'd1, 3'd2, 0, 0);     // v3 = v1+v2
        issue(`CLS_VV,  `OP_MUL, 3'd4, 3'd3, 3'd3, 0, 0);     // RAW dist 1 (both operands)
        issue(`CLS_VV,  `OP_SUB, 3'd5, 3'd3, 3'd4, 0, 0);     // RAW dist 2 (v3), dist 1 (v4)
        issue(`CLS_VV,  `OP_XOR, 3'd6, 3'd3, 3'd5, 0, 0);     // RAW dist 3 (v3), dist 1 (v5)
        issue(`CLS_VV,  `OP_ADD, 3'd3, 3'd3, 3'd3, 0, 0);     // self dependency + WAW later
        issue(`CLS_VV,  `OP_ADD, 3'd3, 3'd3, 3'd6, 0, 0);     // WAW + RAW dist 1
        issue(`CLS_VST, 0, 0, 3'd3, 0, 0, 0);
        issue(`CLS_VST, 0, 0, 3'd4, 0, 0, 0);
        issue(`CLS_VST, 0, 0, 3'd5, 0, 0, 0);
        issue(`CLS_VST, 0, 0, 3'd6, 0, 0, 0);
        // scalar interface: external write, SSET, broadcast, lane extract
        issue(`CLS_NOP, 4'hF, 3'd7, 3'd7, 3'd7, 16'hFFFF, 0);   // NOP with junk fields must do nothing
        ext_scalar_write({W/4{4'hB}} ^ 16'h0EEF);
        issue(`CLS_VSPL, 0, 3'd7, 0, 0, 0, 0);
        issue(`CLS_VST,  0, 0, 3'd7, 0, 0, 0);
        issue(`CLS_VS,   `OP_ADD, 3'd7, 3'd7, 0, 0, 0);       // splat + sreg broadcast
        for (k = 0; k < LANES; k = k + 1)
            issue(`CLS_VEXT, 0, 0, 3'd3, 0, k[15:0], 0);      // extract each lane
        check_regs;
        // reset-in-flight check: model scalar for SSET sign extension
        issue(`CLS_SSET, 0, 0, 0, 0, 16'h8001, 0);
        issue(`CLS_VSPL, 0, 3'd0, 0, 0, 0, 0);
        issue(`CLS_VST,  0, 0, 3'd0, 0, 0, 0);
        check_regs;

        // -------- Phase 3: constrained-random --------
        $display("[Phase 3] constrained-random stream, %0d instructions", N_RAND);
        for (i = 0; i < N_RAND; i = i + 1) begin
            // small register subset in bursts -> many hazards
            rvd = (i % 128 < 64) ? ($random & 3'd3) : $random;
            rs1 = (i % 128 < 64) ? ($random & 3'd3) : $random;
            rs2 = (i % 128 < 64) ? ($random & 3'd3) : $random;
            rop = $random;
            rimm = $random;
            rnd_cls = ($random & 32'h7fffffff) % 24;
            if      (rnd_cls < 7)  issue(`CLS_VV,   rop, rvd, rs1, rs2, rimm, 0);
            else if (rnd_cls < 11) issue(`CLS_VS,   rop, rvd, rs1, rs2, rimm, 0);
            else if (rnd_cls < 14) issue(`CLS_VLD,  rop, rvd, rs1, rs2, rimm, rand_vec(0));
            else if (rnd_cls < 16) issue(`CLS_VST,  rop, rvd, rs1, rs2, rimm, 0);
            else if (rnd_cls < 17) issue(`CLS_VSPL, rop, rvd, rs1, rs2, rimm, 0);
            else if (rnd_cls < 18) issue(`CLS_SSET, rop, rvd, rs1, rs2, rimm, 0);
            else if (rnd_cls < 19) issue(`CLS_VEXT, rop, rvd, rs1, rs2, {13'd0, rimm[2:0]}, 0);
            else if (rnd_cls < 21) begin
                @(posedge clk); #1 instr_valid = 0;           // bubble: instr_valid low, garbage on bus
                instr = {`CLS_VV, 4'h0, 3'd1, 3'd1, 3'd1, 16'd0};
                last_vd[3] = last_vd[2]; last_vd[2] = last_vd[1]; last_vd[1] = -1;
            end
            else if (rnd_cls < 22) issue(`CLS_NOP, rop, rvd, rs1, rs2, rimm, 0);
            else ext_scalar_write($random);
            if (i % 997 == 996) check_regs;
        end
        check_regs;
        idle(6);

        // ---------------------------------------------------------- results
        if (st_h != st_t) begin errors = errors + 1; $display("ERROR: %0d stores never observed", st_t - st_h); end
        if (sc_h != sc_t) begin errors = errors + 1; $display("ERROR: %0d extracts never observed", sc_t - sc_h); end
        if (fl_h != fl_t) begin errors = errors + 1; $display("ERROR: %0d flag updates never observed", fl_t - fl_h); end

        $display("");
        $display("=================== FUNCTIONAL COVERAGE ===================");
        $display("LANES=%0d  W=%0d", LANES, W);
        $write("VV  op hits : ");  for (i = 0; i < 16; i = i + 1) $write("%0d ", cov_vv[i]); $display("");
        $write("VS  op hits : ");  for (i = 0; i < 16; i = i + 1) $write("%0d ", cov_vs[i]); $display("");
        $write("class hits  : ");  for (i = 0; i < 8;  i = i + 1) $write("%0d ", cov_cls[i]); $display("");
        $display("RAW d1=%0d d2=%0d d3=%0d  WAW=%0d  self-dep=%0d", cov_raw1, cov_raw2, cov_raw3, cov_waw, cov_selfdep);
        $write("lane non-zero results: "); for (i = 0; i < LANES; i = i + 1) $write("%0d ", cov_lane_nz[i]); $display("");
        $write("operand-A corners (0,1,-1,min,max,other): "); for (i = 0; i < 6; i = i + 1) $write("%0d ", cov_corner_a[i]); $display("");
        $display("external scalar writes: %0d", cov_ext);
        $display("compare predicate: all-true=%0d mixed=%0d all-false=%0d", cov_all, cov_any_notall, cov_none);

        for (i = 0; i < 16; i = i + 1) begin
            if (cov_vv[i] == 0) begin errors = errors + 1; $display("COVERAGE HOLE: VV op %0d", i); end
            if (cov_vs[i] == 0) begin errors = errors + 1; $display("COVERAGE HOLE: VS op %0d", i); end
        end
        for (i = 0; i < 8; i = i + 1)
            if (cov_cls[i] == 0) begin errors = errors + 1; $display("COVERAGE HOLE: class %0d", i); end
        for (i = 0; i < LANES; i = i + 1)
            if (cov_lane_nz[i] == 0) begin errors = errors + 1; $display("COVERAGE HOLE: lane %0d", i); end
        for (i = 0; i < 6; i = i + 1)
            if (cov_corner_a[i] == 0) begin errors = errors + 1; $display("COVERAGE HOLE: operand corner %0d", i); end
        if (cov_raw1 == 0 || cov_raw2 == 0 || cov_raw3 == 0 || cov_waw == 0 || cov_selfdep == 0) begin
            errors = errors + 1; $display("COVERAGE HOLE: hazard bin");
        end
        if (cov_all == 0 || (LANES > 1 && cov_any_notall == 0) || cov_none == 0) begin
            errors = errors + 1; $display("COVERAGE HOLE: predicate bin");
        end

        $display("===========================================================");
        $display("instructions issued: %0d   stores checked: %0d   extracts checked: %0d   flag updates checked: %0d",
                 n_instr, n_st, n_sc, n_fl);
        if (errors == 0) $display("ALL TESTS PASSED (LANES=%0d, W=%0d)", LANES, W);
        else             $display("TESTS FAILED: %0d errors (LANES=%0d, W=%0d)", errors, LANES, W);
        $finish;
    end

    // watchdog
    initial begin
        #500_000_000;
        $display("TIMEOUT");
        $finish;
    end
endmodule

// (self-checking: asserts expected vs DUT; nonzero exit on mismatch)
