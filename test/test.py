# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

# ── Bit positions in ui_in ──────────────────────────────────────
COIN_1_BIT       = 0
COIN_2_BIT       = 1
COIN_5_BIT       = 2
COIN_10_BIT      = 3
FLOW_SENSOR_BIT  = 4

# ── Bit positions in uo_out ─────────────────────────────────────
VALVE_BIT        = 0   # uo_out[0]
# liters[6:0]  → uo_out[7:1]
# liters[7]    → uio_out[0]


def get_liters(dut):
    """Reconstruct 8-bit liters from uo_out[7:1] + uio_out[0]."""
    low7 = (int(dut.uo_out.value) >> 1) & 0x7F
    msb  = int(dut.uio_out.value) & 0x01
    return (msb << 7) | low7


def get_valve(dut):
    return int(dut.uo_out.value) & 0x01


async def pulse_coin(dut, bit, cycles=2):
    """Assert a coin input for `cycles` clock cycles then deassert."""
    dut.ui_in.value = (1 << bit)
    await ClockCycles(dut.clk, cycles)
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 1)


async def pulse_flow(dut, pulses):
    """Send `pulses` flow-sensor pulses (1 cycle high, 1 cycle low each)."""
    for _ in range(pulses):
        dut.ui_in.value = (1 << FLOW_SENSOR_BIT)
        await ClockCycles(dut.clk, 1)
        dut.ui_in.value = 0
        await ClockCycles(dut.clk, 1)


@cocotb.test()
async def test_project(dut):
    dut._log.info("=== Water ATM TinyTapeout Test Start ===")

    # Start 10 us clock (100 kHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # ── Reset ───────────────────────────────────────────────────
    dut._log.info("Applying reset")
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    dut.rst_n.value  = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value  = 1
    await ClockCycles(dut.clk, 5)

    # ── Test Rs 1 → expect 2 L ──────────────────────────────────
    dut._log.info("Test: coin Rs 1 → 2 litres")
    await pulse_coin(dut, COIN_1_BIT)
    await ClockCycles(dut.clk, 5)          # let FSM reach DISP

    assert get_valve(dut) == 1, "Valve should be ON after Rs1 coin"

    await pulse_flow(dut, 2)
    await ClockCycles(dut.clk, 10)

    assert get_valve(dut) == 0,  "Valve should be OFF after 2 L dispensed"
    assert get_liters(dut) == 2, f"Expected 2 L, got {get_liters(dut)}"
    dut._log.info(f"Rs1 OK  → liters={get_liters(dut)}")

    await ClockCycles(dut.clk, 10)

    # ── Test Rs 2 → expect 5 L ──────────────────────────────────
    dut._log.info("Test: coin Rs 2 → 5 litres")
    await pulse_coin(dut, COIN_2_BIT)
    await ClockCycles(dut.clk, 5)

    assert get_valve(dut) == 1, "Valve should be ON after Rs2 coin"

    await pulse_flow(dut, 5)
    await ClockCycles(dut.clk, 10)

    assert get_valve(dut) == 0,  "Valve should be OFF after 5 L dispensed"
    assert get_liters(dut) == 5, f"Expected 5 L, got {get_liters(dut)}"
    dut._log.info(f"Rs2 OK  → liters={get_liters(dut)}")

    await ClockCycles(dut.clk, 10)

    # ── Test Rs 5 → expect 20 L ─────────────────────────────────
    dut._log.info("Test: coin Rs 5 → 20 litres")
    await pulse_coin(dut, COIN_5_BIT)
    await ClockCycles(dut.clk, 5)

    assert get_valve(dut) == 1, "Valve should be ON after Rs5 coin"

    await pulse_flow(dut, 20)
    await ClockCycles(dut.clk, 10)

    assert get_valve(dut) == 0,   "Valve should be OFF after 20 L dispensed"
    assert get_liters(dut) == 20, f"Expected 20 L, got {get_liters(dut)}"
    dut._log.info(f"Rs5 OK  → liters={get_liters(dut)}")

    await ClockCycles(dut.clk, 10)

    # ── Test Rs 10 → expect 40 L ────────────────────────────────
    dut._log.info("Test: coin Rs 10 → 40 litres")
    await pulse_coin(dut, COIN_10_BIT)
    await ClockCycles(dut.clk, 5)

    assert get_valve(dut) == 1, "Valve should be ON after Rs10 coin"

    await pulse_flow(dut, 40)
    await ClockCycles(dut.clk, 10)

    assert get_valve(dut) == 0,   "Valve should be OFF after 40 L dispensed"
    assert get_liters(dut) == 40, f"Expected 40 L, got {get_liters(dut)}"
    dut._log.info(f"Rs10 OK → liters={get_liters(dut)}")

    # ── Timeout safety test (no flow pulses) ────────────────────
    dut._log.info("Test: timeout — insert Rs1, give NO flow pulses")
    await ClockCycles(dut.clk, 10)
    await pulse_coin(dut, COIN_1_BIT)
    await ClockCycles(dut.clk, 30)   # exceed time_limit=20 cycles

    assert get_valve(dut) == 0, "Valve should be OFF after timeout"
    dut._log.info("Timeout OK")

    dut._log.info("=== All tests passed ===")
