
module tx_logic (
    input logic clk,
    input logic rst_n ,
    input logic [7:0] tx_data,
    input logic tx_en,
    input logic [2:0] baud_rate,
    output logic tx_out,
    output logic tx_busy
);


    typedef enum logic [1:0] {
        IDLE  = 2'b00,
        START = 2'b01,
        DATA  = 2'b11,
        STOP  = 2'b10
    } state_t;


    // Waveform dump for simulation only
    // initial begin
    //     $dumpfile("tx_logic.vcd");
    //     $dumpvars(0, tx_logic);
    // end

    logic [3:0]  bit_count;
    logic [15:0] counter;
    logic [7:0] tx_shift_reg;
    logic baud_tick;
    state_t current_state, next_state;

    // Combinational logic block
    always_comb begin
        // Default assignment prevents latches
        next_state = current_state;

        case (current_state)
            IDLE:  if (tx_en)                          next_state = START;
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

    // Sequential logic for bit counting and data loading
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bit_count <= 0;
            tx_shift_reg <= 0;
        end else begin
            if (current_state == START && next_state == DATA) begin
                tx_shift_reg <= tx_data;
            end
            if (baud_tick) begin
                if (current_state == DATA) begin
                    if (bit_count == 7)
                        bit_count <= 0;
                    else
                        bit_count <= bit_count + 1;
                end else begin
                    bit_count <= 0;
                end
            end
        end
    end

    // Combinational output logic (Moore machine)
    always_comb begin
        // Default outputs
        tx_out = 1'b1;
        tx_busy = 1'b0;

        case (current_state)
            IDLE: begin
                    tx_out = 1'b1;
                    tx_busy = 1'b0;
                  end
            START: begin
                    tx_out = 1'b0;
                    tx_busy = 1'b1;
                   end
            DATA: begin
                    tx_out = tx_shift_reg[bit_count];
                    tx_busy = 1'b1;
                  end
            STOP: begin
                    tx_out = 1'b1;
                    tx_busy = 1'b1;
                  end
            default: begin
                    tx_out = 1'b1;
                    tx_busy = 1'b0;
                  end
        endcase
    end
endmodule
