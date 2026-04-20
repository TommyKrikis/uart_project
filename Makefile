SIM                      ?= icarus
TOPLEVEL                  = top_level
COCOTB_TEST_MODULES       = top_test
VERILOG_SOURCES           = $(PWD)/top.sv $(PWD)/tx_logic.sv $(PWD)/rx_logic.sv
COCOTB_HDL_TIMEUNIT      = 1ns
COCOTB_HDL_TIMEPRECISION = 1ns
COCOTB_MAKEFILES          = $(PWD)/venv/lib/python3.12/site-packages/cocotb_tools/makefiles
PYTHON_BIN                = $(PWD)/venv/bin/python


include $(COCOTB_MAKEFILES)/Makefile.sim
