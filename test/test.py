# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

# ui_in bit positions
COIN_1_BIT      = 0
COIN_2_BIT      = 1
COIN_5_BIT      = 2
COIN_10_BIT     = 3
FLOW_SENSOR_BIT = 4


def get_liters(dut):
    """Reconstruct 8-bit liters: uo_out[7:1]=liters[6:0], uio_out[0]=liters[7]"""
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
    await ClockCycles(dut.clk, 15)
    dut.rst_n.value  = 1
    await ClockCycles(dut.clk, 10)


async def insert_coin(dut, bit):
    """Assert coin for 5 cycles, deassert, then wait for FSM to reach DISP."""
    dut.ui_in.value = (1 << bit)
    await ClockCycles(dut.clk, 5)
    dut.ui_in.value = 0
    # FSM: IDLE->SET (1 cycle) -> DISP (1 cycle) + gate delay margin
    await ClockCycles(dut.clk, 10)


async def send_flow_pulses(dut, count):
    """
    Send 'count' flow-sensor pulses.
    Each pulse: 8 cycles HIGH then 8 cycles LOW.
    8 cycles HIGH ensures the 2-FF synchronizer (with gate delays) reliably
    captures the pulse even in gate-level simulation with UNIT_DELAY=#1.
    """
    for _ in range(count):
        dut.ui_in.value = (1 << FLOW_SENSOR_BIT)
        await ClockCycles(dut.clk, 8)
        dut.ui_in.value = 0
        await ClockCycles(dut.clk, 8)


async def wait_valve_off(dut, max_cycles=600):
    """Wait until valve_on goes low (FSM dispensed all water or timed out)."""
    for _ in range(max_cycles):
        await ClockCycles(dut.clk, 1)
        if get_valve(dut) == 0:
            break
    await ClockCycles(dut.clk, 5)


@cocotb.test()
async def test_project(dut):
    dut._log.info("=== Water ATM TinyTapeout Test Start ===")

    # 10 us clock (100 kHz)
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    # ── Reset ──────────────────────────────────────────────
    dut._log.info("Applying reset")
    await do_reset(dut)

    # ── Test Rs 1 → expect 2 L ─────────────────────────────
    dut._log.info("Test: coin Rs1 -> 2 litres")
    await insert_coin(dut, COIN_1_BIT)

    assert get_valve(dut) == 1, \
        f"Rs1: valve should be ON, uo_out={int(dut.uo_out.value):#010b}"

    await send_flow_pulses(dut, 2)
    await wait_valve_off(dut)

    liters = get_liters(dut)
    assert liters == 2, f"Rs1: Expected 2 L, got {liters}"
    dut._log.info(f"Rs1 PASS -> liters={liters}")
    await ClockCycles(dut.clk, 20)

    # ── Test Rs 2 → expect 5 L ─────────────────────────────
    dut._log.info("Test: coin Rs2 -> 5 litres")
    await insert_coin(dut, COIN_2_BIT)

    assert get_valve(dut) == 1, \
        f"Rs2: valve should be ON, uo_out={int(dut.uo_out.value):#010b}"

    await send_flow_pulses(dut, 5)
    await wait_valve_off(dut)

    liters = get_liters(dut)
    assert liters == 5, f"Rs2: Expected 5 L, got {liters}"
    dut._log.info(f"Rs2 PASS -> liters={liters}")
    await ClockCycles(dut.clk, 20)

    # ── Test Rs 5 → expect 20 L ────────────────────────────
    dut._log.info("Test: coin Rs5 -> 20 litres")
    await insert_coin(dut, COIN_5_BIT)

    assert get_valve(dut) == 1, \
        f"Rs5: valve should be ON, uo_out={int(dut.uo_out.value):#010b}"

    await send_flow_pulses(dut, 20)
    await wait_valve_off(dut)

    liters = get_liters(dut)
    assert liters == 20, f"Rs5: Expected 20 L, got {liters}"
    dut._log.info(f"Rs5 PASS -> liters={liters}")
    await ClockCycles(dut.clk, 20)

    # ── Test Rs 10 → expect 40 L ───────────────────────────
    dut._log.info("Test: coin Rs10 -> 40 litres")
    await insert_coin(dut, COIN_10_BIT)

    assert get_valve(dut) == 1, \
        f"Rs10: valve should be ON, uo_out={int(dut.uo_out.value):#010b}"

    await send_flow_pulses(dut, 40)
    await wait_valve_off(dut)

    liters = get_liters(dut)
    assert liters == 40, f"Rs10: Expected 40 L, got {liters}"
    dut._log.info(f"Rs10 PASS -> liters={liters}")
    await ClockCycles(dut.clk, 20)

    # ── Timeout test: insert Rs1, give NO flow pulses ──────
    dut._log.info("Test: timeout - Rs1 coin, no flow pulses")
    await insert_coin(dut, COIN_1_BIT)
    assert get_valve(dut) == 1, "Timeout test: valve should be ON at start"

    # time_limit for Rs1 = 20 cycles; wait well past that
    await ClockCycles(dut.clk, 50)

    assert get_valve(dut) == 0, "Timeout test: valve should be OFF after timeout"
    dut._log.info("Timeout PASS")

    dut._log.info("=== All tests PASSED ===")
