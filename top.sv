module top_level (

	input logic clk,
	input logic rst_n ,
    input  logic [7:0] uart_in,
    output logic [7:0] uart_out
);
    logic enable = 1'b1;
    logic [2:0] baud_rate = 3'b000;
	logic rx_busy;
	logic tx_busy;
	logic internal_sig;
   
    // Waveform dump for simulation only
    initial begin
        $dumpfile("top.vcd");
        $dumpvars(0, top_level);
    end



    // Instantiate the tx module
    tx_logic module_tx (
        .clk(clk),
        .rst_n(rst_n),
        .tx_data(uart_in),
        .tx_en(enable),
        .baud_rate(baud_rate),
        .tx_out(internal_sig),
        .tx_busy(tx_busy)
    );

	 // Instantiate the rx module
    rx_logic module_rx (
        .clk(clk), 
        .rst_n(rst_n), 
        .rx_data(internal_sig),
        .rx_en(enable),
        .baud_rate(baud_rate),
        .rx_out(uart_out),
        .rx_busy(rx_busy)
    );
endmodule
