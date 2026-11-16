// -----------------------------------------------------------------------------
// result_combiner : gathers the per-lane results into the vector result bus and
// derives the compare predicate (one bit per lane) plus ANY / ALL reductions.
// The predicate is meaningful after a compare operation (lane result is 0 / all-ones).
// -----------------------------------------------------------------------------
module result_combiner #(
    parameter LANES = 4,
    parameter W     = 16
) (
    input  wire [LANES*W-1:0] lane_y,     // concatenated lane results (lane 0 = LSBs)
    output wire [LANES*W-1:0] vec_y,      // combined vector result
    output wire [LANES-1:0]   mask,       // lane predicate (bit l = LSB of lane l)
    output wire               any_lane,
    output wire               all_lanes
);
    assign vec_y = lane_y;

    genvar l;
    generate
        for (l = 0; l < LANES; l = l + 1) begin : g_mask
            assign mask[l] = lane_y[l*W];
        end
    endgenerate

    assign any_lane  = |mask;
    assign all_lanes = &mask;
endmodule

// (reviewed: port widths / params consistent with simd_defs.vh)
