// -----------------------------------------------------------------------------
// vreg_file : 8 vector registers, VW bits wide (VW = LANES*W).
//   2 asynchronous read ports, 1 synchronous write port.
//   Write-through (bypass): a read of the register being written in the same
//   cycle returns the new data, so back-to-back dependent instructions never stall.
// -----------------------------------------------------------------------------
module vreg_file #(
    parameter VW = 64
) (
    input  wire          clk,
    input  wire          rst,
    input  wire [2:0]    ra1,
    input  wire [2:0]    ra2,
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

    assign rd1 = (we && (wa == ra1)) ? wd : regs[ra1];
    assign rd2 = (we && (wa == ra2)) ? wd : regs[ra2];
endmodule
