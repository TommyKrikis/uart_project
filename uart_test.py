# ============================================================
#  uart_test.py  –  A beginner-friendly cocotb testbench
#  for the UART TX module (tx_logic.sv)
# ============================================================
#
#  WHAT IS COCOTB?
#  cocotb lets you write testbenches in Python instead of
#  SystemVerilog/VHDL.  It runs alongside your simulator
#  (here: Icarus Verilog) and drives the DUT's (Device Under
#  Test) inputs / reads its outputs just like a real circuit
#  would.
#
#  KEY IDEA: everything is async/await.
#  Because hardware runs in time, we can't just call functions
#  and get instant results.  We use "await" to say:
#  "pause this test here, let simulation time advance, then
#  continue once the condition is met."
# ============================================================

import cocotb
from cocotb.clock import Clock          # helper that drives the clk signal
from cocotb.triggers import RisingEdge  # "await" this to wait one clock edge
from cocotb.triggers import Timer       # "await" this to wait a fixed time


# ------------------------------------------------------------
# HELPER FUNCTION 1:  apply_reset
# ------------------------------------------------------------
# A good test always starts with a clean reset.
# This function drives rst_n low for a few cycles then releases it.
#
# "async def" means the function can use "await" inside it.
# "dut" is the Python object that represents your SystemVerilog
# module – its ports are accessed as dut.port_name.value
# ------------------------------------------------------------
async def apply_reset(dut):
    # Drive all inputs to safe default values BEFORE reset
    dut.rst_n.value  = 0   # active-low reset  → assert it (0 = reset active)
    dut.tx_en.value  = 0   # don't request a transmission yet
    dut.tx_data.value = 0  # doesn't matter during reset, but avoids X

    # Wait two rising edges so the reset is registered cleanly
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    # Release reset
    dut.rst_n.value = 1

    # One more cycle to let the design settle after reset release
    await RisingEdge(dut.clk)


# ------------------------------------------------------------
# HELPER FUNCTION 2:  wait_for_baud_tick
# ------------------------------------------------------------
# The baud generator inside tx_logic pulses "baud_tick" high
# for one clock cycle every 11 clocks (counter counts 0→10).
# The FSM only advances its state when baud_tick is high.
#
# This helper just loops on rising clock edges until it sees
# baud_tick go high.  It also has a safety counter so the test
# doesn't hang forever if something is broken.
# ------------------------------------------------------------
async def wait_for_baud_tick(dut, max_cycles=50):
    for _ in range(max_cycles):
        await RisingEdge(dut.clk)   # advance one clock
        if dut.baud_tick.value == 1:
            return  # baud_tick is high → done
    # If we reach here, we never saw a tick → the test should fail
    raise RuntimeError("Timeout: baud_tick never went high!")


# ============================================================
#  TEST 1:  test_reset
# ============================================================
# The simplest possible test: after reset, the TX line must be
# idle (logic 1) and the module must not be busy.
#
# @cocotb.test()  registers this function as a test case.
# The simulator will run it automatically.
# ============================================================
@cocotb.test()
async def test_reset(dut):
    """After reset, tx_out should be 1 (idle) and tx_busy should be 0."""

    # 1. Start a 10 ns clock (100 MHz).
    #    cocotb.start_soon() launches the clock "in the background"
    #    so our test coroutine and the clock run concurrently.
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # 2. Apply reset
    await apply_reset(dut)

    # 3. Check outputs
    #    assert <condition>, "message shown if it fails"
    assert dut.tx_out.value  == 1, f"tx_out should be 1 after reset, got {dut.tx_out.value}"
    assert dut.tx_busy.value == 0, f"tx_busy should be 0 after reset, got {dut.tx_busy.value}"

    dut._log.info("test_reset PASSED")


# ============================================================
#  TEST 2:  test_idle_without_tx_en
# ============================================================
# Even after reset, if we never assert tx_en, the line must
# stay idle forever.  This checks that the module doesn't
# spontaneously start transmitting.
# ============================================================
@cocotb.test()
async def test_idle_without_tx_en(dut):
    """tx_out must stay 1 and tx_busy must stay 0 when tx_en is never asserted."""

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await apply_reset(dut)

    # Wait for several baud ticks without driving tx_en
    for tick_num in range(5):
        await wait_for_baud_tick(dut)
        assert dut.tx_out.value  == 1, f"tx_out changed unexpectedly on tick {tick_num}"
        assert dut.tx_busy.value == 0, f"tx_busy went high unexpectedly on tick {tick_num}"

    dut._log.info("test_idle_without_tx_en PASSED")


# ============================================================
#  TEST 3:  test_start_bit
# ============================================================
# When we assert tx_en, the very first thing the UART does is
# send a START bit, which is logic 0.
#
# UART frame looks like this over time:
#   ___      _______________      ___
#      |    |               |    |
#   1  | 0  | D0 D1 ... D7  | 1  |  (then idle again)
#      |    |               |    |
#    IDLE START   DATA BITS  STOP
# ============================================================
@cocotb.test()
async def test_start_bit(dut):
    """After tx_en is asserted, the first baud tick should produce a START bit (tx_out = 0)."""

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await apply_reset(dut)

    # Assert tx_en to request a transmission
    dut.tx_en.value   = 1
    dut.tx_data.value = 0xA5   # the byte we want to send (doesn't matter for this test)

    # Wait for the first baud tick – the FSM should move IDLE → START
    await wait_for_baud_tick(dut)

    # In the START state: tx_out must be 0, tx_busy must be 1
    assert dut.tx_out.value  == 0, f"Start bit should be 0, got {dut.tx_out.value}"
    assert dut.tx_busy.value == 1, f"tx_busy should be 1 during START, got {dut.tx_busy.value}"

    dut._log.info("test_start_bit PASSED")


# ============================================================
#  TEST 4:  test_full_byte
# ============================================================
# This is the main test.  We send one complete byte (0xA5) and
# verify every bit on tx_out in order.
#
# 0xA5 = 1010_0101 in binary.
# UART sends LSB first, so the order on the wire is:
#   bit0=1, bit1=0, bit2=1, bit3=0, bit4=0, bit5=1, bit6=0, bit7=1
# ============================================================
@cocotb.test()
async def test_full_byte(dut):
    """Transmit 0xA5 and verify every bit that appears on tx_out."""

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await apply_reset(dut)

    TEST_BYTE = 0xA5
    # Build a list of the 8 bits we expect, LSB first
    expected_bits = [(TEST_BYTE >> i) & 1 for i in range(8)]
    # For 0xA5: [1, 0, 1, 0, 0, 1, 0, 1]

    dut._log.info(f"Sending 0x{TEST_BYTE:02X}, expected bits (LSB first): {expected_bits}")

    # --- Kick off the transmission ---
    dut.tx_en.value   = 1
    dut.tx_data.value = TEST_BYTE

    # --- START bit ---
    await wait_for_baud_tick(dut)   # FSM: IDLE → START
    assert dut.tx_out.value == 0, "Start bit must be 0"
    dut._log.info("START bit OK (tx_out=0)")

    # --- 8 DATA bits ---
    for i, expected in enumerate(expected_bits):
        await wait_for_baud_tick(dut)   # FSM advances on every tick
        actual = int(dut.tx_out.value)
        assert actual == expected, (
            f"Data bit {i}: expected {expected}, got {actual}"
        )
        dut._log.info(f"  bit[{i}] = {actual}  (expected {expected})  ✓")

    # --- STOP bit ---
    # After the 8th data bit tick the FSM moves to STOP.
    # The last wait_for_baud_tick above already put us in STOP,
    # so we just read tx_out right now.
    assert dut.tx_out.value  == 1, "Stop bit must be 1"
    assert dut.tx_busy.value == 1, "tx_busy must still be 1 during STOP"
    dut._log.info("STOP bit OK (tx_out=1)")

    # --- Back to IDLE ---
    await wait_for_baud_tick(dut)   # FSM: STOP → IDLE
    await RisingEdge(dut.clk)       # one extra edge to let outputs settle

    assert dut.tx_out.value  == 1, "After STOP, tx_out must return to 1 (idle)"
    assert dut.tx_busy.value == 0, "After STOP, tx_busy must return to 0"
    dut._log.info("Back to IDLE  ✓")

    dut._log.info("test_full_byte PASSED")
