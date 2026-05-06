/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */
`default_nettype none

module tt_um_water_atm (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

    // ── Input mapping ──────────────────────────────────────────
    wire coin_1      = ui_in[0];
    wire coin_2      = ui_in[1];
    wire coin_5      = ui_in[2];
    wire coin_10     = ui_in[3];
    wire flow_sensor = ui_in[4];
    wire rst         = ~rst_n;   // TT uses active-low reset

    // ── Internal signals ───────────────────────────────────────
    wire       valve_on;
    wire [7:0] liters;

    // ── Output mapping ─────────────────────────────────────────
    assign uo_out  = {liters[6:0], valve_on}; // uo_out[0]=valve, [7:1]=liters[6:0]
    assign uio_out = {7'b0, liters[7]};        // uio_out[0] = liters MSB
    assign uio_oe  = 8'b0000_0001;             // uio[0] is output, rest inputs

    // ── Unused input suppression ───────────────────────────────
    wire _unused = &{ena, ui_in[7:5], uio_in, 1'b0};

    // ── Core module instantiation ──────────────────────────────
    water_atm core (
        .clk         (clk),
        .rst         (rst),
        .coin_1      (coin_1),
        .coin_2      (coin_2),
        .coin_5      (coin_5),
        .coin_10     (coin_10),
        .flow_sensor (flow_sensor),
        .valve_on    (valve_on),
        .liters      (liters)
    );

endmodule


// ================================================================
//  Core Water ATM FSM
// ================================================================
module water_atm (
    input  wire       clk,
    input  wire       rst,
    input  wire       coin_1,
    input  wire       coin_2,
    input  wire       coin_5,
    input  wire       coin_10,
    input  wire       flow_sensor,
    output reg        valve_on,
    output reg  [7:0] liters
);

    localparam IDLE = 2'd0,
               SET  = 2'd1,
               DISP = 2'd2,
               DONE = 2'd3;

    reg [1:0]  state;
    reg [7:0]  target;
    reg [7:0]  coin_reg;
    reg [7:0]  coin_value;
    reg [15:0] timer;
    reg [15:0] time_limit;

    // ── Flow sensor 2-FF synchronizer ──────────────────────────
    reg flow_d1, flow_d2;
    always @(posedge clk) begin
        flow_d1 <= flow_sensor;
        flow_d2 <= flow_d1;
    end
    wire flow_sync = flow_d2;

    // ── FSM ────────────────────────────────────────────────────
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            state      <= IDLE;
            liters     <= 8'd0;
            valve_on   <= 1'b0;
            coin_reg   <= 8'd0;
            coin_value <= 8'd0;
            target     <= 8'd0;
            timer      <= 16'd0;
            time_limit <= 16'd0;
        end else begin
            case (state)

                // -------- IDLE --------
                IDLE: begin
                    liters   <= 8'd0;
                    valve_on <= 1'b0;
                    timer    <= 16'd0;
                    if      (coin_1)  begin coin_reg <= 8'd1;  state <= SET; end
                    else if (coin_2)  begin coin_reg <= 8'd2;  state <= SET; end
                    else if (coin_5)  begin coin_reg <= 8'd5;  state <= SET; end
                    else if (coin_10) begin coin_reg <= 8'd10; state <= SET; end
                end

                // -------- SET --------
                SET: begin
                    case (coin_reg)
                        8'd1:  begin target <= 8'd2;  time_limit <= 16'd20;  end
                        8'd2:  begin target <= 8'd5;  time_limit <= 16'd50;  end
                        8'd5:  begin target <= 8'd20; time_limit <= 16'd200; end
                        8'd10: begin target <= 8'd40; time_limit <= 16'd400; end
                        default: begin target <= 8'd0; time_limit <= 16'd0; end
                    endcase
                    coin_value <= coin_reg;
                    timer      <= 16'd0;
                    state      <= DISP;
                end

                // -------- DISP --------
                DISP: begin
                    valve_on <= 1'b1;
                    timer    <= timer + 16'd1;
                    if (flow_sync && (liters < target)) begin
                        liters <= liters + 8'd1;
                    end
                    if ((liters >= target && target != 8'd0) ||
                        (timer >= time_limit)) begin
                        valve_on <= 1'b0;
                        state    <= DONE;
                    end
                end

                // -------- DONE --------
                DONE: begin
                    state <= IDLE;
                end

                default: state <= IDLE;
            endcase
        end
    end

endmodule
