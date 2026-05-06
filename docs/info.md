## How it works

This project is a **Water ATM system** implemented using a Finite State Machine (FSM).

The system accepts coin inputs and dispenses water accordingly.

### Working:

1. System starts in IDLE state
2. When a coin is inserted:
   - ₹1 → 2 liters
   - ₹2 → 5 liters
   - ₹5 → 20 liters
   - ₹10 → 40 liters
3. The valve turns ON
4. Flow sensor generates pulses
5. Each pulse = 1 liter
6. When required liters reached OR timeout:
   - Valve turns OFF
   - System resets

---

## How to test

1. Apply reset (`rst_n = 0 → 1`)
2. Insert coin using:
   - ui[0] = ₹1
   - ui[1] = ₹2
   - ui[2] = ₹5
   - ui[3] = ₹10
3. Provide flow pulses using:
   - ui[4] (flow sensor)
4. Observe:
   - uo[0] → valve status
   - uo[7:1] + uio[0] → liters

Example:

- Insert ₹1 → give 2 pulses → valve OFF
- Insert ₹2 → give 5 pulses → valve OFF

---

## External hardware

- Flow sensor (pulse output)
- Solenoid valve
- Coin acceptor
