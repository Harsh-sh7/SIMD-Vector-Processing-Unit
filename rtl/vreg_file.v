// -----------------------------------------------------------------------------
// vreg_file : 8 vector registers, VW bits wide (VW = LANES*W).
//   2 asynchronous read ports, 1 synchronous write port.
//   Bypass (write-through): when byp1/byp2 is set (computed one cycle early by the
//   hazard unit) the read port returns the data being written this cycle instead of
//   the stored value, so back-to-back dependent instructions never stall.
// -----------------------------------------------------------------------------
module vreg_file #(
    parameter VW = 64
) (
    input  wire          clk,
    input  wire          rst,
    input  wire [2:0]    ra1,
    input  wire [2:0]    ra2,
    input  wire          byp1,
    input  wire          byp2,
    output wire [VW-1:0] rd1,
    output wire [VW-1:0] rd2,
    input  wire          we,
    input  wire [2:0]    wa,
    input  wire [VW-1:0] wd
);
    reg [VW-1:0] regs [0:7];
    integer i;

    always @(posedge clk) begin
        if (rst) begin
            for (i = 0; i < 8; i = i + 1) regs[i] <= {VW{1'b0}};
        end else if (we) begin
            regs[wa] <= wd;
        end
    end

    assign rd1 = byp1 ? wd : regs[ra1];
    assign rd2 = byp2 ? wd : regs[ra2];
endmodule
