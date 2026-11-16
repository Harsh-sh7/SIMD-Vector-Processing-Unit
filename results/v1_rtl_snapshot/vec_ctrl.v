// -----------------------------------------------------------------------------
// vec_ctrl : vector control unit
//   * decodes the instruction register into datapath control signals
//   * hosts the hardware performance counters (cycles, instructions, lane-ops)
// -----------------------------------------------------------------------------
`include "simd_defs.vh"

module vec_ctrl #(
    parameter LANES = 4
) (
    input  wire        clk,
    input  wire        rst,
    input  wire [31:0] instr,        // instruction register (execute stage)

    // decoded controls
    output wire [3:0]  op,
    output wire [2:0]  vd,
    output wire [2:0]  vs1,
    output wire [2:0]  vs2,
    output wire [15:0] imm,
    output wire        alu_en,       // VV or VS operation
    output wire        use_sc,       // operand B comes from scalar broadcast
    output wire [1:0]  res_sel,
    output wire        reg_we,       // write a vector register
    output wire        st_en,        // vector store
    output wire        sset_en,      // scalar register write
    output wire        vext_en,      // lane extract

    // performance counters
    input  wire        perf_clr,
    output reg  [31:0] perf_cycles,
    output reg  [31:0] perf_instr,
    output reg  [31:0] perf_laneops
);
    wire [2:0] cls = instr[31:29];

    assign op  = instr[28:25];
    assign vd  = instr[24:22];
    assign vs1 = instr[21:19];
    assign vs2 = instr[18:16];
    assign imm = instr[15:0];

    assign alu_en  = (cls == `CLS_VV) || (cls == `CLS_VS);
    assign use_sc  = (cls == `CLS_VS);
    assign res_sel = (cls == `CLS_VLD)  ? `RES_LD  :
                     (cls == `CLS_VSPL) ? `RES_SPL : `RES_ALU;
    assign reg_we  = alu_en || (cls == `CLS_VLD) || (cls == `CLS_VSPL);
    assign st_en   = (cls == `CLS_VST);
    assign sset_en = (cls == `CLS_SSET);
    assign vext_en = (cls == `CLS_VEXT);

    wire valid = (cls != `CLS_NOP);

    always @(posedge clk) begin
        if (rst || perf_clr) begin
            perf_cycles  <= 32'd0;
            perf_instr   <= 32'd0;
            perf_laneops <= 32'd0;
        end else begin
            perf_cycles <= perf_cycles + 32'd1;
            if (valid)  perf_instr   <= perf_instr + 32'd1;
            if (alu_en) perf_laneops <= perf_laneops + LANES;
        end
    end
endmodule
