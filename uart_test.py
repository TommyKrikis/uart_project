import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.handle import SimHandleBase   

def enable_vcd(dut: SimHandleBase, filename="tx_logic.vcd"):
    """Attach a VCD dump to the simulation (Icarus only)."""
    dut._log.info(f"VCD → {filename}")
    dut._dumpfile = filename
    dut._dumpvars = 0   # dump all hierarchy levels

@cocotb.test()
async def test_reset(dut):
    # enable_vcd(dut)
    
    """tx_out should be 0 after reset."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    dut.rst.value = 0        # assert active-low reset
    dut.tx_en.value = 0
    dut.tx_data.value = 1

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    assert dut.tx_out.value == 0, f"Expected 0 after reset, got {dut.tx_out.value}"

@cocotb.test()
async def test_transmit(dut):
    # enable_vcd(dut)

    """tx_out should follow tx_data when tx_en is high."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    # Release reset
    dut.rst.value = 1
    dut.tx_en.value = 1

    for data_bit in [0, 1, 1, 0, 1]:
        dut.tx_data.value = data_bit
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)   # give one cycle to propagate
        assert dut.tx_out.value == data_bit, \
            f"Expected {data_bit}, got {dut.tx_out.value}"

@cocotb.test()
async def test_tx_en_gate(dut):
    # enable_vcd(dut)

    """tx_out should NOT change when tx_en is low."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    dut.rst.value = 1
    dut.tx_en.value = 1
    dut.tx_data.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    # Now disable tx_en and change data — output must hold
    dut.tx_en.value = 0
    dut.tx_data.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    assert dut.tx_out.value == 1, \
        f"tx_out should be held at 1, got {dut.tx_out.value}"
