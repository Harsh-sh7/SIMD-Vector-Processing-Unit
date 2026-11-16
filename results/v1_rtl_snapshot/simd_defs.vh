// -----------------------------------------------------------------------------
// simd_defs.vh : opcode / instruction-class encodings shared by RTL and testbenches
//
// 32-bit vector instruction format
//   [31:29] cls  instruction class
//   [28:25] op   lane-ALU operation (used by VV / VS classes)
//   [24:22] vd   destination vector register  (v0..v7)
//   [21:19] vs1  source vector register 1
//   [18:16] vs2  source vector register 2
//   [15:0]  imm  immediate (SSET value / VEXT lane index)
// -----------------------------------------------------------------------------
`ifndef SIMD_DEFS_VH
`define SIMD_DEFS_VH

// ---- lane ALU operations -----------------------------------------------------
`define OP_ADD  4'h0   // a + b
`define OP_SUB  4'h1   // a - b
`define OP_AND  4'h2   // a & b
`define OP_OR   4'h3   // a | b
`define OP_XOR  4'h4   // a ^ b
`define OP_SLL  4'h5   // a << b[log2(W)-1:0]
`define OP_SRL  4'h6   // a >> b[log2(W)-1:0]  (logical)
`define OP_SRA  4'h7   // a >>> b[log2(W)-1:0] (arithmetic)
`define OP_MUL  4'h8   // low W bits of a * b
`define OP_EQ   4'h9   // a == b          -> all-ones / zero lane mask
`define OP_NE   4'hA   // a != b          -> all-ones / zero lane mask
`define OP_LT   4'hB   // a <  b (signed) -> all-ones / zero lane mask
`define OP_GT   4'hC   // a >  b (signed) -> all-ones / zero lane mask
`define OP_LTU  4'hD   // a <  b (unsigned)-> all-ones / zero lane mask
`define OP_MIN  4'hE   // signed minimum
`define OP_MAX  4'hF   // signed maximum

// ---- instruction classes -----------------------------------------------------
`define CLS_NOP   3'd0
`define CLS_VV    3'd1  // vd = vs1 (op) vs2
`define CLS_VS    3'd2  // vd = vs1 (op) splat(sreg)       (scalar operand broadcast)
`define CLS_VLD   3'd3  // vd = ld_data                    (vector load from external bus)
`define CLS_VST   3'd4  // st_data = vs1                   (vector store to external bus)
`define CLS_VSPL  3'd5  // vd = splat(sreg)                (broadcast scalar into all lanes)
`define CLS_SSET  3'd6  // sreg = sign_extend(imm)         (scalar register write)
`define CLS_VEXT  3'd7  // scalar_out = lane[imm] of vs1   (extract lane to scalar side)

// ---- result-mux select ---------------------------------------------------------
`define RES_ALU   2'd0
`define RES_LD    2'd1
`define RES_SPL   2'd2

`endif
