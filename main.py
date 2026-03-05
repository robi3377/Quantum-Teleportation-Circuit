import os
import warnings
import numpy as np
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.quantum_info import Statevector
from qiskit.visualization import plot_bloch_multivector, plot_histogram

try:
    from qiskit_aer import AerSimulator
    AER_AVAILABLE = True
except ImportError:
    AER_AVAILABLE = False
    print("WARNING: qiskit-aer not found. Install with: pip install qiskit-aer")


# state to teleport: |psi> = cos(theta/2)|0> + e^(i*phi)*sin(theta/2)|1>
THETA = np.pi / 3   # 60 degrees
PHI   = np.pi / 4   # 45 degrees
SHOTS = 2048*2
OUTPUT_DIR = "images"


def get_message_statevector(theta, phi):
    qc = QuantumCircuit(1)
    qc.u(theta, phi, 0, 0)
    return Statevector.from_label('0').evolve(qc)


def build_teleportation_circuit(theta, phi):
    qr = QuantumRegister(3, 'q')
    cr = ClassicalRegister(3, 'c')
    circuit = QuantumCircuit(qr, cr)

    # step 1: prepare the message qubit
    circuit.u(theta, phi, 0, qr[0])
    circuit.barrier()

    # step 2: create Bell pair on q[1] and q[2]
    circuit.h(qr[1])
    circuit.cx(qr[1], qr[2])
    circuit.barrier()

    # step 3: Alice's Bell measurement
    circuit.cx(qr[0], qr[1])
    circuit.h(qr[0])
    circuit.barrier()
    circuit.measure(qr[0], cr[0])   # c[0] -> Z correction
    circuit.measure(qr[1], cr[1])   # c[1] -> X correction
    circuit.barrier()

    # step 4: Bob applies corrections based on classical bits
    with circuit.if_test((cr[1], 1)):
        circuit.x(qr[2])
    with circuit.if_test((cr[0], 1)):
        circuit.z(qr[2])

    return circuit


def build_verification_circuit(theta, phi):
    # same as above but applies U-inverse at the end and measures q[2]
    # if q[2] == |psi> then U†|psi> = |0>, so c[2] should always be 0
    qr = QuantumRegister(3, 'q')
    cr = ClassicalRegister(3, 'c')
    circuit = QuantumCircuit(qr, cr)

    circuit.u(theta, phi, 0, qr[0])
    circuit.barrier()
    circuit.h(qr[1])
    circuit.cx(qr[1], qr[2])
    circuit.barrier()
    circuit.cx(qr[0], qr[1])
    circuit.h(qr[0])
    circuit.barrier()
    circuit.measure(qr[0], cr[0])
    circuit.measure(qr[1], cr[1])
    circuit.barrier()
    with circuit.if_test((cr[1], 1)):
        circuit.x(qr[2])
    with circuit.if_test((cr[0], 1)):
        circuit.z(qr[2])
    circuit.barrier()

    # U†(theta, phi, 0) = U(-theta, 0, -phi)
    circuit.u(-theta, 0, -phi, qr[2])
    circuit.measure(qr[2], cr[2])

    return circuit


def run_on_simulator(circuit, shots=SHOTS):
    if not AER_AVAILABLE:
        raise RuntimeError("Install qiskit-aer: pip install qiskit-aer")
    simulator = AerSimulator()
    transpiled = transpile(circuit, simulator)
    job = simulator.run(transpiled, shots=shots)
    return job.result().get_counts()


def analyze_results(main_counts, verification_counts):
    total = sum(main_counts.values())

    # qiskit bit strings: rightmost char = c[0], second from right = c[1]
    alice_dist = {}
    for outcome_str, count in main_counts.items():
        bits = outcome_str.replace(' ', '')
        c0 = int(bits[-1])
        c1 = int(bits[-2]) if len(bits) >= 2 else 0
        key = (c0, c1)
        alice_dist[key] = alice_dist.get(key, 0) + count

    corrections = {
        (0, 0): "no correction",
        (1, 0): "Z applied",
        (0, 1): "X applied",
        (1, 1): "X then Z applied",
    }

    print(f"\nAlice's measurement outcomes ({total} shots):")
    for (c0, c1), count in sorted(alice_dist.items()):
        pct = 100.0 * count / total
        label = corrections.get((c0, c1), "?")
        print(f"  c[0]={c0}, c[1]={c1}: {count} shots ({pct:.1f}%) -> {label}")

    # all four outcomes should be ~25% each (random by design)
    all_near_25 = all(abs(100.0 * c / total - 25.0) < 5.0 for c in alice_dist.values())
    print("  -> distribution looks uniform" if all_near_25 else "  -> check circuit, distribution looks off")

    # verification: c[2] is leftmost character in result string
    total_v = sum(verification_counts.values())
    c2_zero = sum(v for k, v in verification_counts.items() if k.replace(' ', '')[0] == '0')
    c2_one  = sum(v for k, v in verification_counts.items() if k.replace(' ', '')[0] == '1')
    print(f"\nVerification (c[2] after inverse gate):")
    print(f"  c[2]=0 (success): {c2_zero}/{total_v} ({100*c2_zero/total_v:.1f}%)")
    print(f"  c[2]=1 (failure): {c2_one}/{total_v} ({100*c2_one/total_v:.1f}%)")
    if c2_one == 0:
        print("  -> teleportation verified, c[2] is 0 in every shot")
    else:
        print("  -> something went wrong, check circuit")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Quantum Teleportation Circuit")
    print(f"Teleporting: |psi> = cos({THETA/2:.3f})|0> + e^(i*{PHI:.3f})*sin({THETA/2:.3f})|1>")
    print(f"theta={np.degrees(THETA):.1f} deg, phi={np.degrees(PHI):.1f} deg\n")

    # --- initial state ---
    print("[1/4] Computing initial state...")
    sv = get_message_statevector(THETA, PHI)
    print(f"  statevector: {[f'{c:.4f}' for c in sv.data]}")

    fig = plot_bloch_multivector(sv, title="Initial state (Alice's qubit)")
    fig.savefig(f"{OUTPUT_DIR}/bloch_initial.png", dpi=150, bbox_inches='tight')
    plt.close(fig)

    fig = plot_bloch_multivector(sv, title="Expected final state (Bob's qubit)")
    fig.savefig(f"{OUTPUT_DIR}/bloch_final_expected.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  saved Bloch sphere plots to {OUTPUT_DIR}/")

    # --- build circuit ---
    print("\n[2/4] Building teleportation circuit...")
    circuit = build_teleportation_circuit(THETA, PHI)
    print(f"  depth: {circuit.depth()}, gates: {circuit.count_ops()}")
    print(circuit.draw('text', fold=150))

    try:
        fig = circuit.draw('mpl', fold=80, style='iqp')
        fig.savefig(f"{OUTPUT_DIR}/teleportation_circuit.png", dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"  saved: {OUTPUT_DIR}/teleportation_circuit.png")
    except Exception as e:
        print(f"  (matplotlib draw skipped: {e})")

    # --- run simulation ---
    print(f"\n[3/4] Running simulation ({SHOTS} shots)...")
    main_counts = run_on_simulator(circuit)
    print(f"  counts: {main_counts}")
    fig = plot_histogram(main_counts, title="Alice's measurements (expect ~25% each)")
    fig.savefig(f"{OUTPUT_DIR}/histogram_alice_measurements.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  saved: {OUTPUT_DIR}/histogram_alice_measurements.png")

    # --- verification ---
    print(f"\n[4/4] Running verification circuit ({SHOTS} shots)...")
    verification_circuit = build_verification_circuit(THETA, PHI)
    verification_counts = run_on_simulator(verification_circuit)
    print(f"  counts: {verification_counts}")

    try:
        fig = verification_circuit.draw('mpl', fold=80, style='iqp')
        fig.savefig(f"{OUTPUT_DIR}/verification_circuit.png", dpi=150, bbox_inches='tight')
        plt.close(fig)
    except Exception:
        pass

    fig = plot_histogram(verification_counts, title="Verification (c[2]=0 means success)")
    fig.savefig(f"{OUTPUT_DIR}/histogram_verification.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  saved verification plots to {OUTPUT_DIR}/")

    # --- results ---
    analyze_results(main_counts, verification_counts)

    print(f"\nDone. Figures saved to {OUTPUT_DIR}/")

    # IBM hardware note (need qiskit-ibm-runtime installed and account set up)
    print("\n-- To run on real IBM hardware, uncomment the block below --")
    # from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
    # service = QiskitRuntimeService()
    # backend = service.least_busy(operational=True, simulator=False, min_num_qubits=3)
    # hw_circuit = transpile(circuit, backend=backend, optimization_level=3)
    # sampler = Sampler(mode=backend)
    # job = sampler.run([hw_circuit], shots=1024)
    # print(f"Job ID: {job.job_id()}")
    # hw_counts = job.result()[0].data.c.get_counts()
    # print(hw_counts)


if __name__ == '__main__':
    main()
