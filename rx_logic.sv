module rx_logic (
    input logic clk,
    input logic rst_n ,
    input logic rx_data,
    input logic rx_en,
    input logic [2:0] baud_rate,
    output logic [7:0] rx_out,
    output logic rx_busy
);


    typedef enum logic [1:0] {
        IDLE  = 2'b00,
        START = 2'b01,
        DATA  = 2'b11,
        STOP  = 2'b10
    } state_t;


    // // Waveform dump for simulation only
    // initial begin
    //     $dumpfile("rx_logic.vcd");
    //     $dumpvars(0, rx_logic);
    // end
    
	logic [3:0]  bit_count;
    logic [15:0] counter;
    logic [7:0] rx_shift_reg;
    logic baud_tick;
    state_t current_state, next_state;

	// Combinational logic block
    always_comb begin
        // Default assignment prevents latches
        next_state = current_state;

        case (current_state)
            IDLE:  if (rx_en && !rx_data)              next_state = START;
            START: if (baud_tick)                      next_state = DATA;
            DATA:  if (baud_tick && bit_count == 7)    next_state = STOP;
            STOP:  if (baud_tick)                      next_state = IDLE;
            default:                                   next_state = IDLE;
        endcase
    end
    
    // Sequential logic block for state storage
        always_ff @(posedge clk or negedge rst_n) begin
            if (!rst_n) current_state <= IDLE;  // Asynchronous reset to known state
            else        current_state <= next_state;
        end

    // Sequential logic block for BAUD
        always_ff @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                counter <= 0;
                baud_tick <= 0;
            end else begin
                baud_tick <= 0;
                if (counter == 10) begin
                    counter <= 0;
                    baud_tick <= 1;
                end else begin
                    counter <= counter + 1;
                end
            end
        end

        // Sequential logic for bit counting and data capture
            always_ff @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    bit_count <= 0;
                    rx_shift_reg <= 8'h00;
                    rx_out <= 8'h00;
                end else begin
                    if (baud_tick && current_state == DATA) begin
                        rx_shift_reg[bit_count] <= rx_data;
                        if (bit_count == 7)
                            bit_count <= 0;
                        else
                            bit_count <= bit_count + 1;
                    end else if (baud_tick) begin
                        bit_count <= 0;
                    end

                    if (baud_tick && current_state == STOP) begin
						rx_out <= rx_shift_reg;
                    end
                end
            end

            always_comb begin
                // Default outputs
                rx_busy = 1'b0;
                case (current_state)
                    IDLE: begin
                            rx_busy = 1'b0;
                          end
                    START: begin
                            rx_busy = 1'b1;
                           end
                    DATA: begin
                            rx_busy = 1'b1;
                          end
                    STOP: begin
                            rx_busy = 1'b1;
                          end
                    default: begin
                            rx_busy = 1'b0;
                          end
                endcase
           end
endmodule
