// -----------------------------------------------------------------------------
// vec_ctrl : vector control unit
//   * stage F : decodes the incoming instruction and REGISTERS all control signals,
//               so the execute stage starts from flip-flops (no decode logic on the
//               critical path)
//   * hazard unit : pre-computes, one cycle early, whether each source operand of the
//               instruction entering E must be bypassed from the write-back stage
//   * hosts the hardware performance counters (cycles, instructions, lane-ops)
// -----------------------------------------------------------------------------
`include "simd_defs.vh"

module vec_ctrl #(
    parameter LANES = 4
) (
    input  wire        clk,
    input  wire        rst,
    input  wire [31:0] instr_in,     // stage-F instruction (already forced to NOP when invalid)

    // registered controls for the execute stage
    output reg  [3:0]  op,
    output reg  [2:0]  vd,
    output reg  [2:0]  vs1,
    output reg  [2:0]  vs2,
    output reg  [15:0] imm,
    output reg         alu_en,       // VV or VS operation
    output reg         use_sc,       // operand B comes from scalar broadcast
    output reg  [1:0]  res_sel,
    output reg         reg_we,       // write a vector register
    output reg         st_en,        // vector store
    output reg         sset_en,      // scalar register write
    output reg         vext_en,      // lane extract
    output reg         byp1,         // vs1 must be forwarded from write-back stage
    output reg         byp2,         // vs2 must be forwarded from write-back stage

    // performance counters
    input  wire        perf_clr,
    output reg  [31:0] perf_cycles,
    output reg  [31:0] perf_instr,
    output reg  [31:0] perf_laneops
);
    // ---- combinational decode of the stage-F instruction ----
    wire [2:0] cls_n   = instr_in[31:29];
    wire       alu_n   = (cls_n == `CLS_VV) || (cls_n == `CLS_VS);
    wire       we_n    = alu_n || (cls_n == `CLS_VLD) || (cls_n == `CLS_VSPL);
    wire [1:0] ressel_n = (cls_n == `CLS_VLD)  ? `RES_LD  :
                          (cls_n == `CLS_VSPL) ? `RES_SPL : `RES_ALU;

    reg valid;                                   // E-stage instruction is not a NOP

    always @(posedge clk) begin
        if (rst) begin
            op <= 4'd0; vd <= 3'd0; vs1 <= 3'd0; vs2 <= 3'd0; imm <= 16'd0;
            alu_en <= 1'b0; use_sc <= 1'b0; res_sel <= `RES_ALU;
            reg_we <= 1'b0; st_en <= 1'b0; sset_en <= 1'b0; vext_en <= 1'b0;
            byp1 <= 1'b0; byp2 <= 1'b0; valid <= 1'b0;
        end else begin
            op      <= instr_in[28:25];
            vd      <= instr_in[24:22];
            vs1     <= instr_in[21:19];
            vs2     <= instr_in[18:16];
            imm     <= instr_in[15:0];
            alu_en  <= alu_n;
            use_sc  <= (cls_n == `CLS_VS);
            res_sel <= ressel_n;
            reg_we  <= we_n;
            st_en   <= (cls_n == `CLS_VST);
            sset_en <= (cls_n == `CLS_SSET);
            vext_en <= (cls_n == `CLS_VEXT);
            valid   <= (cls_n != `CLS_NOP);
            // Hazard unit: the instruction now in E (reg_we/vd, being written back next
            // cycle) is the producer for the instruction now in F (consumer, in E next cycle).
            byp1    <= reg_we && (vd == instr_in[21:19]);
            byp2    <= reg_we && (vd == instr_in[18:16]);
        end
    end

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
