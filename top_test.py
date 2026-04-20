import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


BAUD_DIV_CYCLES = 11
FRAME_BITS = 10  # start + 8 data + stop


async def apply_reset(dut):
    dut.rst_n.value = 0
    dut.uart_in.value = 0x00
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def wait_cycles(dut, cycles):
    for _ in range(cycles):
        await RisingEdge(dut.clk)


async def send_and_wait_frame(dut, byte_value):
    dut.uart_in.value = byte_value
    # tx/rx run from the same baud generator; wait one full UART frame.
    await wait_cycles(dut, BAUD_DIV_CYCLES * FRAME_BITS + 20)


async def wait_for_uart_out_value(dut, expected, max_frames=3):
    for _ in range(max_frames):
        await wait_cycles(dut, BAUD_DIV_CYCLES * FRAME_BITS + 20)
        if int(dut.uart_out.value) == expected:
            return
    raise AssertionError(
        f"Timed out waiting for uart_out=0x{expected:02X}, got 0x{int(dut.uart_out.value):02X}"
    )


@cocotb.test()
async def test_loopback_bytes(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await apply_reset(dut)

    test_bytes = [0x00, 0x55, 0xA3, 0xFF]
    for value in test_bytes:
        dut.uart_in.value = value
        await wait_for_uart_out_value(dut, value)


@cocotb.test()
async def test_uart_out_stable_after_frame(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await apply_reset(dut)

    value = 0x3C
    await send_and_wait_frame(dut, value)
    first_capture = int(dut.uart_out.value)
    assert first_capture == value, (
        f"Expected 0x{value:02X} after frame, got 0x{first_capture:02X}"
    )

    # With uart_in unchanged, subsequent frames should keep producing same value.
    await send_and_wait_frame(dut, value)
    second_capture = int(dut.uart_out.value)
    assert second_capture == value, (
        f"Value changed unexpectedly: expected 0x{value:02X}, got 0x{second_capture:02X}"
    )
