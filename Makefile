SIM                      ?= icarus
TOPLEVEL                  = tx_logic
COCOTB_TEST_MODULES       = uart_test
VERILOG_SOURCES           = $(PWD)/tx_logic.sv
COCOTB_HDL_TIMEUNIT      = 1ns
COCOTB_HDL_TIMEPRECISION = 1ns



include $(shell cocotb-config --makefiles)/Makefile.sim
