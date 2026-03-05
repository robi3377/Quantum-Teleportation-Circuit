# Quantum Teleportation Circuit

Implementation of the 3-qubit quantum teleportation protocol using Qiskit.
Built as a learning project while studying quantum computing.

---

## What is Quantum Teleportation?

Quantum teleportation transfers a qubit's quantum state from Alice to Bob using
pre-shared entanglement and 2 classical bits — without the physical qubit ever
travelling between them.

It's not teleportation in the sci-fi sense. No matter moves. What moves is the
*quantum state* (the amplitudes), and Alice's original qubit gets destroyed in
the process. The protocol also requires a classical communication channel, so it
can't beat the speed of light.

It matters because it's a core primitive for quantum networks, distributed
quantum computing, and quantum error correction.

---

## Background

A qubit is in a superposition `|ψ⟩ = α|0⟩ + β|1⟩` where α and β are complex
amplitudes with `|α|² + |β|² = 1`. Measuring collapses it to either 0 or 1,
destroying the superposition.

Two qubits can be **entangled** — their states are correlated in a way that
can't be explained by classical probability. The Bell state used here is:

```
|Φ+⟩ = (|00⟩ + |11⟩)/√2
```

Created by applying H to one qubit, then CNOT:

```
|00⟩ → (H⊗I) → (|0⟩+|1⟩)/√2 ⊗ |0⟩ → (CNOT) → (|00⟩+|11⟩)/√2
```

---

## The Protocol

3 qubits:
- `q[0]` — Alice's message qubit, holds `|ψ⟩ = α|0⟩ + β|1⟩`
- `q[1]` — Alice's half of the Bell pair
- `q[2]` — Bob's half of the Bell pair (teleportation destination)

```
q[0]: ──[U(θ,φ)]──●──[H]──[M]────────────────────────
                   │              |
q[1]: ──[H]──●────⊕────────[M]───┼───────────────────
             │                   |         |
q[2]: ───────⊕──────────────[c_if X]──[c_if Z]──[|ψ⟩]
```

**Step 1** — Prepare the message: apply `U(θ, φ, 0)` to `q[0]`.

**Step 2** — Create the Bell pair: H on `q[1]`, then CNOT(`q[1]` → `q[2]`).

**Step 3** — Alice's Bell measurement: CNOT(`q[0]` → `q[1]`), H(`q[0]`),
then measure both. This destroys `|ψ⟩` on `q[0]`.

**Step 4** — Alice sends her 2 classical bits to Bob (over any classical channel).

**Step 5** — Bob applies corrections depending on the bits:

| c[0] | c[1] | Bob's qubit | Correction |
|------|------|-------------|------------|
| 0 | 0 | α\|0⟩ + β\|1⟩ | none |
| 0 | 1 | α\|1⟩ + β\|0⟩ | X gate |
| 1 | 0 | α\|0⟩ - β\|1⟩ | Z gate |
| 1 | 1 | α\|1⟩ - β\|0⟩ | X then Z |

After corrections, `q[2]` is in state `|ψ⟩`. Teleportation complete.

---

## Installation

```bash
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

pip install qiskit qiskit-aer matplotlib numpy
```

---

## Running

```bash
python main.py
```

The script builds the teleportation circuit, runs 2048 shots on AerSimulator,
and saves plots to `output/`:

- `bloch_initial.png` — Alice's initial qubit state
- `bloch_final_expected.png` — what Bob's qubit should look like
- `teleportation_circuit.png` — the full circuit diagram
- `verification_circuit.png` — the verification circuit
- `histogram_alice_measurements.png` — Alice's outcomes (~25% each, random by design)
- `histogram_verification.png` — Bob's verification qubit (should always be 0)

To change the state being teleported, edit `THETA` and `PHI` at the top of `main.py`.
Some interesting ones: `THETA=0` teleports `|0⟩`, `THETA=np.pi/2, PHI=0` teleports
`|+⟩`.

---

## Understanding the Output

Alice's 4 measurement outcomes should each appear ~25% of the time. This is expected —
the result is genuinely random and teleportation works for all four cases.

The verification circuit applies `U†` (the inverse of the preparation gate) to Bob's
qubit after teleportation. If it worked, `q[2]` is in `|ψ⟩`, so `U†|ψ⟩ = |0⟩` and
the verification bit `c[2]` must always read 0. On a simulator it should be 100%.

---

## IBM Hardware

To run on a real quantum device, install `qiskit-ibm-runtime`, set up an account
at [quantum.ibm.com](https://quantum.ibm.com), and uncomment the hardware block
at the bottom of `main.py`. Real hardware will show ~3-8% error on the verification
qubit due to gate noise and decoherence — that's normal.
