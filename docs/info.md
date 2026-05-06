## How it works

The **Water ATM** is a coin-operated water dispenser implemented as a 4-state
Mealy/Moore FSM in Verilog.

**States:**

| State | Action |
|-------|--------|
| `IDLE` | Waits for a coin input. Resets litre counter and closes valve. |
| `SET`  | Decodes the coin value and loads the target volume and safety time-limit. |
| `DISP` | Opens the valve (`valve_on = 1`) and counts incoming flow-sensor pulses until the target volume is reached or the timer expires. |
| `DONE` | Closes the valve and returns to `IDLE` in the next cycle. |

**Coin → Water mapping:**

| Coin | Volume | Safety time-limit |
|------|--------|-------------------|
| Rs 1  |  2 L  | 20 clock cycles  |
| Rs 2  |  5 L  | 50 clock cycles  |
| Rs 5  | 20 L  | 200 clock cycles |
| Rs 10 | 40 L  | 400 clock cycles |

The flow sensor input passes through a 2-flip-flop synchroniser to prevent
metastability before it is used by the FSM.

The 8-bit litre counter is split across the output pins:
`liters[6:0]` → `uo_out[7:1]`, `liters[7]` → `uio_out[0]`.

## How to test

1. Apply reset by pulling `rst_n` low for at least 10 clock cycles, then
   release it high.
2. Assert exactly **one** coin pin (`ui_in[0..3]`) high for 1–2 clock cycles
   then deassert it. The FSM will move from `IDLE` → `SET` → `DISP`
   automatically.
3. Once `uo_out[0]` (valve_on) goes high, start toggling `ui_in[4]`
   (flow_sensor) — one high→low pulse per litre dispensed.
4. After the target volume of pulses, `valve_on` will go low automatically.
   Read the dispensed volume from `uo_out[7:1]` (bits 6:0) and `uio_out[0]`
   (bit 7).
5. The design returns to `IDLE` automatically — repeat from step 2 for the
   next transaction.
6. A **safety timeout** closes the valve if no flow pulses arrive within the
   time-limit, preventing the valve from staying open indefinitely.

You can verify all four coin scenarios with the provided cocotb `test.py`.

## External hardware

| Hardware | Purpose |
|----------|---------|
| Solenoid valve (5 V / 12 V) | Controlled by `valve_on` output (via MOSFET/relay driver) |
| YF-S201 flow sensor or similar | Generates one pulse per litre on `flow_sensor` input |
| Coin acceptor module (4-output) | Drives coin_1 / coin_2 / coin_5 / coin_10 inputs |

> **Note:** All external hardware must be level-shifted to 3.3 V logic before
> connecting to the TinyTapeout PCB.
