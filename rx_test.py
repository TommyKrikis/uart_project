# ============================================================
#  rx_test.py  –  A simple cocotb testbench for the RX module
#  (rx_logic.sv)
# ============================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


async def apply_reset(dut):
    """Reset the RX module."""
    dut.rst_n.value = 0
    dut.rx_data.value = 1  # UART idle state is high
    dut.rx_en.value = 0
    dut.baud_rate.value = 0

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_reset(dut):
    """After reset, rx_busy should be 0."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await apply_reset(dut)

    assert dut.rx_busy.value == 0, f"rx_busy should be 0 after reset, got {dut.rx_busy.value}"
    dut._log.info("test_reset PASSED")


@cocotb.test()
async def test_rx_full_byte(dut):
    """Send one byte via rx_data and verify it's received correctly."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await apply_reset(dut)

    TEST_BYTE = 0xA5  # 1010_0101 in binary
    expected_bits = [(TEST_BYTE >> i) & 1 for i in range(8)]  # LSB first

    dut._log.info(f"Receiving 0x{TEST_BYTE:02X}, expected bits (LSB first): {expected_bits}")

    # Enable reception
    dut.rx_en.value = 1

    # Wait a few cycles for rx_en to be seen
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    # Send START bit (logic 0)
    dut._log.info("Sending START bit (0)")
    dut.rx_data.value = 0

    # Wait for START state to be detected (rx_data going low triggers it)
    # Need to wait for the FSM to see rx_en && !rx_data
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    # Now wait for baud tick to enter START state
    while dut.current_state.value != 1:  # START = 2'b01 = 1
        await RisingEdge(dut.clk)

    dut._log.info("RX entered START state")
    assert dut.rx_busy.value == 1, "rx_busy should be 1 during reception"

    # Wait for START baud tick to complete
    while dut.current_state.value == 1:  # Wait until we leave START
        await RisingEdge(dut.clk)

    dut._log.info("RX entered DATA state, sending data bits")

    # Send 8 data bits, one per baud period
    for i, bit in enumerate(expected_bits):
        dut.rx_data.value = bit
        dut._log.info(f"  Sending bit[{i}] = {bit}")

        # Wait for one baud tick (11 clock cycles at counter==10)
        tick_count = 0
        while tick_count < 11:
            await RisingEdge(dut.clk)
            if dut.baud_tick.value == 1:
                tick_count = 0  # Reset when we see a tick
            tick_count += 1

    # Send STOP bit (logic 1)
    dut._log.info("Sending STOP bit (1)")
    dut.rx_data.value = 1

    # Wait for STOP state to complete
    while dut.current_state.value != 0:  # IDLE = 2'b00 = 0
        await RisingEdge(dut.clk)

    # Check received byte
    received = int(dut.rx_out.value)
    assert received == TEST_BYTE, f"Received 0x{received:02X}, expected 0x{TEST_BYTE:02X}"

    dut._log.info(f"Received 0x{received:02X} correctly!")
    assert dut.rx_busy.value == 0, "rx_busy should be 0 after reception completes"

    dut._log.info("test_rx_full_byte PASSED")
