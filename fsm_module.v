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
    localparam [1:0] S_IDLE            = 2'b00,
                     S_WAIT_INPUT      = 2'b01,
                     S_DISPENSE_TEA    = 2'b10,
                     S_DISPENSE_COFFEE = 2'b11;

    reg [1:0] current_state;
    reg [1:0] next_state;

    // 1st Always Block: State Register (Sequential)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            current_state <= S_IDLE;
        end else begin
            current_state <= next_state;
        end
    end

    // 2nd Always Block: Next State Logic (Combinational)
    always @(*) begin
        next_state = current_state;
        case (current_state)
            S_IDLE: begin
                if (coin_inserted) begin
                    next_state = S_WAIT_INPUT;
                end
            end
            S_WAIT_INPUT: begin
                if (sel_tea) begin
                    next_state = S_DISPENSE_TEA;
                end else if (sel_coffee) begin
                    next_state = S_DISPENSE_COFFEE;
                end
            end
            S_DISPENSE_TEA: begin
                if (completed) begin
                    next_state = S_IDLE;
                end
            end
            S_DISPENSE_COFFEE: begin
                if (completed) begin
                    next_state = S_IDLE;
                end
            end
            default: begin
                next_state = S_IDLE;
            end
        endcase
    end

    // 3rd Always Block: Output Logic (Combinational - Moore Style)
    always @(*) begin
        // Default outputs to avoid latches
        dispense_tea_out    = 1'b0;
        dispense_coffee_out = 1'b0;
        
        case (current_state)
            S_IDLE: begin
                dispense_tea_out    = 1'b0;
                dispense_coffee_out = 1'b0;
            end
            S_WAIT_INPUT: begin
                dispense_tea_out    = 1'b0;
                dispense_coffee_out = 1'b0;
            end
            S_DISPENSE_TEA: begin
                dispense_tea_out    = 1'b1;
                dispense_coffee_out = 1'b0;
            end
            S_DISPENSE_COFFEE: begin
                dispense_tea_out    = 1'b0;
                dispense_coffee_out = 1'b1;
            end
            default: begin
                dispense_tea_out    = 1'b0;
                dispense_coffee_out = 1'b0;
            end
        endcase
    end

endmodule