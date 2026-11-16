// -----------------------------------------------------------------------------
// simd_vpu : SIMD Vector Processing Unit (top level)
//
//   LANES identical W-bit ALU lanes execute one vector instruction per cycle.
//   3-stage pipeline, 1 instruction/cycle throughput, no stalls (full bypass):
//
//     F : decode + hazard check, registered into control flops (vec_ctrl), load-bus capture (ld_q)
//     E : vreg read (+bypass), lane MUXes, LANES x ALU, result combine
//     W : vector register write-back            (wb_*)
//
//   Interfaces
//     instr / instr_valid   : one 32-bit vector instruction per cycle
//     ld_data               : LANES*W-bit load bus, sampled together with a VLD
//     st_valid / st_data    : vector store bus, registered, valid 2 cycles after VST issue
//     scalar_we / scalar_in : optional scalar interface - write the scalar register
//     sc_valid / scalar_out : optional scalar interface - lane extracted by VEXT
//     vmask / vany / vall   : compare predicate of the last vector ALU result
// -----------------------------------------------------------------------------
`include "simd_defs.vh"

module simd_vpu #(
    parameter LANES = 4,
    parameter W     = 16
) (
    input  wire               clk,
    input  wire               rst,

    input  wire               instr_valid,
    input  wire [31:0]        instr,
    input  wire [LANES*W-1:0] ld_data,

    input  wire               scalar_we,
    input  wire [W-1:0]       scalar_in,

    output reg                st_valid,
    output reg  [LANES*W-1:0] st_data,
    output reg                sc_valid,
    output reg  [W-1:0]       scalar_out,

    output reg                flags_valid,
    output reg  [LANES-1:0]   vmask,
    output reg                vany,
    output reg                vall,

    input  wire               perf_clr,
    output wire [31:0]        perf_cycles,
    output wire [31:0]        perf_instr,
    output wire [31:0]        perf_laneops
);
    localparam VW = LANES * W;

    // ------------------------------------------------------------------ stage F
    // Load-bus capture. The instruction itself is decoded and registered by vec_ctrl.
    reg [VW-1:0] ld_q;
    always @(posedge clk) begin
        if (rst)              ld_q <= {VW{1'b0}};
        else if (instr_valid) ld_q <= ld_data;
    end

    // ------------------------------------------------------------------ stage E
    wire [3:0]  op;
    wire [2:0]  vd, vs1, vs2;
    wire [15:0] imm;
    wire        alu_en, use_sc, reg_we, st_en, sset_en, vext_en, byp1, byp2;
    wire [1:0]  res_sel;

    vec_ctrl #(.LANES(LANES)) u_ctrl (
        .clk(clk), .rst(rst), .instr_in(instr_valid ? instr : 32'd0),
        .op(op), .vd(vd), .vs1(vs1), .vs2(vs2), .imm(imm),
        .alu_en(alu_en), .use_sc(use_sc), .res_sel(res_sel),
        .reg_we(reg_we), .st_en(st_en), .sset_en(sset_en), .vext_en(vext_en),
        .byp1(byp1), .byp2(byp2),
        .perf_clr(perf_clr), .perf_cycles(perf_cycles),
        .perf_instr(perf_instr), .perf_laneops(perf_laneops)
    );

    // scalar register (broadcast source)
    reg [W-1:0] sreg;
    always @(posedge clk) begin
        if (rst)            sreg <= {W{1'b0}};
        else if (scalar_we) sreg <= scalar_in;
        else if (sset_en)   sreg <= $signed(imm);
    end

    // write-back stage registers (declared here, used by the register file)
    reg          wb_we;
    reg  [2:0]   wb_vd;
    reg  [VW-1:0] wb_data;

    wire [VW-1:0] rd1, rd2;
    vreg_file #(.VW(VW)) u_rf (
        .clk(clk), .rst(rst),
        .ra1(vs1), .ra2(vs2), .byp1(byp1), .byp2(byp2), .rd1(rd1), .rd2(rd2),
        .we(wb_we), .wa(wb_vd), .wd(wb_data)
    );

    // LANES parallel lanes
    wire [VW-1:0] lane_y;
    genvar l;
    generate
        for (l = 0; l < LANES; l = l + 1) begin : g_lane
            simd_lane #(.W(W)) u_lane (
                .op(op), .use_sc(use_sc), .res_sel(res_sel),
                .a    (rd1[l*W +: W]),
                .b_vec(rd2[l*W +: W]),
                .sc   (sreg),
                .ld   (ld_q[l*W +: W]),
                .y    (lane_y[l*W +: W])
            );
        end
    endgenerate

    wire [VW-1:0]    vec_y;
    wire [LANES-1:0] mask_c;
    wire             any_c, all_c;
    result_combiner #(.LANES(LANES), .W(W)) u_comb (
        .lane_y(lane_y), .vec_y(vec_y), .mask(mask_c),
        .any_lane(any_c), .all_lanes(all_c)
    );

    // lane extract (scalar interface)
    reg [W-1:0] ext_val;
    integer k;
    always @* begin
        ext_val = rd1[0 +: W];
        for (k = 0; k < LANES; k = k + 1)
            if (imm == k) ext_val = rd1[k*W +: W];
    end

    // ---------------------------------------------- E -> W pipeline registers
    always @(posedge clk) begin
        if (rst) begin
            wb_we       <= 1'b0;
            wb_vd       <= 3'd0;
            wb_data     <= {VW{1'b0}};
            st_valid    <= 1'b0;
            st_data     <= {VW{1'b0}};
            sc_valid    <= 1'b0;
            scalar_out  <= {W{1'b0}};
            flags_valid <= 1'b0;
            vmask       <= {LANES{1'b0}};
            vany        <= 1'b0;
            vall        <= 1'b0;
        end else begin
            wb_we       <= reg_we;
            wb_vd       <= vd;
            wb_data     <= vec_y;

            st_valid    <= st_en;
            if (st_en)  st_data <= rd1;

            sc_valid    <= vext_en;
            if (vext_en) scalar_out <= ext_val;

            flags_valid <= alu_en;
            if (alu_en) begin
                vmask <= mask_c;
                vany  <= any_c;
                vall  <= all_c;
            end
        end
    end
endmodule
