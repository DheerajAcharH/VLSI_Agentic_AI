`timescale 1ns / 1ps

module vending_machine (
    input  wire clk,
    input  wire rst_n,
    input  wire coin_inserted,
    input  wire sel_tea,
    input  wire sel_coffee,
    input  wire completed,
    output reg  dispense_tea_out,
    output reg  dispense_coffee_out
);

    // State Encoding
    localparam [1:0] S_IDLE            = 2'b00;
    localparam [1:0] S_WAIT_INPUT      = 2'b01;
    localparam [1:0] S_DISPENSE_TEA    = 2'b10;
    localparam [1:0] S_DISPENSE_COFFEE = 2'b11;

    reg [1:0] state;
    reg [1:0] next_state;

    // Block 1: State Register (Sequential)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
        end else begin
            state <= next_state;
        end
    end

    // Block 2: Next State Logic (Combinational)
    always @* begin
        next_state = state;
        case (state)
            S_IDLE: begin
                if (coin_inserted) begin
                    next_state = S_WAIT_INPUT;
                end else begin
                    next_state = S_IDLE;
                end
            end
            S_WAIT_INPUT: begin
                if (sel_tea) begin
                    next_state = S_DISPENSE_TEA;
                end else if (sel_coffee) begin
                    next_state = S_DISPENSE_COFFEE;
                end else begin
                    next_state = S_WAIT_INPUT;
                end
            end
            S_DISPENSE_TEA: begin
                if (completed) begin
                    next_state = S_IDLE;
                end else begin
                    next_state = S_DISPENSE_TEA;
                end
            end
            S_DISPENSE_COFFEE: begin
                if (completed) begin
                    next_state = S_IDLE;
                end else begin
                    next_state = S_DISPENSE_COFFEE;
                end
            end
            default: begin
                next_state = S_IDLE;
            end
        endcase
    end

    // Block 3: Output Logic (Registered Outputs using next_state)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dispense_tea_out    <= 1'b0;
            dispense_coffee_out <= 1'b0;
        end else begin
            case (next_state)
                S_DISPENSE_TEA: begin
                    dispense_tea_out    <= 1'b1;
                    dispense_coffee_out <= 1'b0;
                end
                S_DISPENSE_COFFEE: begin
                    dispense_tea_out    <= 1'b0;
                    dispense_coffee_out <= 1'b1;
                end
                default: begin
                    dispense_tea_out    <= 1'b0;
                    dispense_coffee_out <= 1'b0;
                end
            endcase
        end
    end

endmodule