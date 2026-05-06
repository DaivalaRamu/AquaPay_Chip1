# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

# ui_in bit positions
COIN_1_BIT      = 0
COIN_2_BIT      = 1
COIN_5_BIT      = 2
COIN_10_BIT     = 3
FLOW_SENSOR_BIT = 4


def get_liters(dut):
    """Reconstruct 8-bit liters: uo_out[7:1] = liters[6:0], uio_out[0] = liters[7]"""
    low7 = (int(dut.uo_out.value) >> 1) & 0x7F
    msb  = int(dut.uio_out.value) & 0x01
    return (msb << 7) | low7


def get_valve(dut):
    return int(dut.uo_out.value) & 0x01


async def do_reset(dut):
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    dut.rst_n.value  = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value  = 1
    await ClockCycles(dut.clk, 5)   # settle after reset


async def insert_coin(dut, bit):
    """Assert coin for 2 cycles, then deassert and wait for FSM to reach DISP."""
    dut.ui_in.value = (1 << bit)
    await ClockCycles(dut.clk, 2)
    dut.ui_in.value = 0
    # FSM needs: IDLE->SET (1 cycle) -> DISP (1 cycle) + sync margin
    await ClockCycles(dut.clk, 5)


async def send_flow_pulses(dut, count):
    """Send 'count' flow-sensor pulses: 2 cycles high, 2 cycles low each."""
    for _ in range(count):
        dut.ui_in.value = (1 << FLOW_SENSOR_BIT)
        await ClockCycles(dut.clk, 2)   # hold high for 2 cycles (passes 2-FF sync)
        dut.ui_in.value = 0
        await ClockCycles(dut.clk, 2)   # gap between pulses


async def wait_for_done(dut, max_cycles=50):
    """Wait until valve turns off (FSM reached DONE/IDLE)."""
    for _ in range(max_cycles):
        await ClockCycles(dut.clk, 1)
        if get_valve(dut) == 0:
            break
    await ClockCycles(dut.clk, 3)   # let FSM return to IDLE


@cocotb.test()
async def test_project(dut):
    dut._log.info("=== Water ATM TinyTapeout Test Start ===")

    # 10 us clock (100 kHz)
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    # ── Reset ──────────────────────────────────────────────────
    dut._log.info("Applying reset")
    await do_reset(dut)

    # ── Test Rs 1 → expect 2 L ─────────────────────────────────
    dut._log.info("Test: coin Rs1 → 2 litres")
    await insert_coin(dut, COIN_1_BIT)

    assert get_valve(dut) == 1, \
        f"Valve should be ON after Rs1 coin, uo_out={int(dut.uo_out.value)}"

    await send_flow_pulses(dut, 2)
    await wait_for_done(dut)

    liters = get_liters(dut)
    assert liters == 2, f"Expected 2 L, got {liters}"
    dut._log.info(f"Rs1 PASS → liters={liters}")

    # ── Test Rs 2 → expect 5 L ─────────────────────────────────
    dut._log.info("Test: coin Rs2 → 5 litres")
    await insert_coin(dut, COIN_2_BIT)

    assert get_valve(dut) == 1, \
        f"Valve should be ON after Rs2 coin, uo_out={int(dut.uo_out.value)}"

    await send_flow_pulses(dut, 5)
    await wait_for_done(dut)

    liters = get_liters(dut)
    assert liters == 5, f"Expected 5 L, got {liters}"
    dut._log.info(f"Rs2 PASS → liters={liters}")

    # ── Test Rs 5 → expect 20 L ────────────────────────────────
    dut._log.info("Test: coin Rs5 → 20 litres")
    await insert_coin(dut, COIN_5_BIT)

    assert get_valve(dut) == 1, \
        f"Valve should be ON after Rs5 coin, uo_out={int(dut.uo_out.value)}"

    await send_flow_pulses(dut, 20)
    await wait_for_done(dut)

    liters = get_liters(dut)
    assert liters == 20, f"Expected 20 L, got {liters}"
    dut._log.info(f"Rs5 PASS → liters={liters}")

    # ── Test Rs 10 → expect 40 L ───────────────────────────────
    dut._log.info("Test: coin Rs10 → 40 litres")
    await insert_coin(dut, COIN_10_BIT)

    assert get_valve(dut) == 1, \
        f"Valve should be ON after Rs10 coin, uo_out={int(dut.uo_out.value)}"

    await send_flow_pulses(dut, 40)
    await wait_for_done(dut)

    liters = get_liters(dut)
    assert liters == 40, f"Expected 40 L, got {liters}"
    dut._log.info(f"Rs10 PASS → liters={liters}")

    # ── Timeout test: insert Rs1, give NO flow pulses ──────────
    dut._log.info("Test: timeout — Rs1 coin, no flow pulses")
    await insert_coin(dut, COIN_1_BIT)
    assert get_valve(dut) == 1, "Valve should be ON at start of timeout test"

    # time_limit for Rs1 = 20 cycles; wait 30 to be safe
    await ClockCycles(dut.clk, 30)

    assert get_valve(dut) == 0, "Valve should be OFF after timeout"
    dut._log.info("Timeout PASS")

    dut._log.info("=== All tests PASSED ===")
