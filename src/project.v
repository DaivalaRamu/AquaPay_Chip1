module tt_um_water_atm (
    input  wire clk,
    input  wire rst_n,

    input  wire [7:0] ui_in,
    output reg  [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe
);

    // Coin inputs
    wire coin1 = ui_in[0];
    wire coin2 = ui_in[1];
    wire coin5 = ui_in[2];
    wire coin10 = ui_in[3];
    wire flow = ui_in[4];

    reg [7:0] liters;
    reg valve;

    assign uio_out = 8'b0;
    assign uio_oe  = 8'b0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            liters <= 0;
            valve <= 0;
        end else begin

            // Coin detection
            if (coin1) begin
                liters <= 2;
                valve <= 1;
            end else if (coin2) begin
                liters <= 5;
                valve <= 1;
            end else if (coin5) begin
                liters <= 20;
                valve <= 1;
            end else if (coin10) begin
                liters <= 40;
                valve <= 1;
            end

            // Flow counting
            if (valve && flow) begin
                if (liters > 0)
                    liters <= liters - 1;

                if (liters == 1)
                    valve <= 0;
            end
        end
    end

    // OUTPUT MAPPING (VERY IMPORTANT)
    always @(*) begin
        uo_out[0] = valve;
        uo_out[7:1] = liters[6:0];
    end

endmodule
