#!/usr/bin/env python3
"""
Kuramoto Energy & Topological Transition Tracking
=================================================

Comprehensive energy analysis across topological phase transitions.
Tracks kinetic energy, coupling energy, dissipation, and topological
winding to understand the energetic cost of Berry phase accumulation.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import cumulative_trapezoid
import json


def stroboscopic_subtraction_filter(t, Z_t, omega_bar_t):
    """Extract geometric phase."""
    phi_total = np.unwrap(np.angle(Z_t))
    phi_dyn = cumulative_trapezoid(omega_bar_t, t, initial=0.0)
    phi_geom_continuous = phi_total - phi_dyn

    mean_carrier_freq = np.mean(omega_bar_t)
    T_0 = (2 * np.pi) / mean_carrier_freq if mean_carrier_freq > 0 else 1.0

    delta_phi_geom = phi_geom_continuous[-1] - phi_geom_continuous[0]
    geometric_winding_nu = delta_phi_geom / (2 * np.pi)

    return {
        "phi_geom": phi_geom_continuous,
        "delta_phi_geom": delta_phi_geom,
        "winding_nu": geometric_winding_nu,
        "carrier_period": T_0
    }


class KuramotoEnergyTracker:
    """
    Kuramoto with comprehensive energy tracking through topological transitions.
    """

    def __init__(self, N=256, K=1.2, phase_cycles=3, sweep_duration=300.0, dt=0.01):
        """Initialize energy-tracking simulator."""
        self.N = N
        self.K = K
        self.phase_cycles = phase_cycles
        self.sweep_duration = sweep_duration
        self.dt = dt
        self.steps = int(sweep_duration / dt)

        # Phase initialization
        mean_phase = np.random.uniform(0, 2*np.pi)
        self.theta = np.mod(np.random.normal(mean_phase, 0.3, N), 2*np.pi)
        self.omega_nat = np.random.normal(1.0, 0.01, N)

        # Create cyclic topological phase
        t_cycle_up = np.linspace(0, 1, self.steps // 2)
        t_cycle_down = np.linspace(1, 0, self.steps - self.steps // 2)
        self.phi_sweep_t = np.concatenate([t_cycle_up, t_cycle_down]) * phase_cycles * 2 * np.pi

        # Metrics
        self.t_vals = []
        self.r_vals = []
        self.phi_sweep_vals = []
        self.Z_vals = []

        # Energy tracking
        self.kinetic_energy = []           # KE = (1/2) * Σ ω_dot²
        self.coupling_energy = []          # CE = -κ * Σ cos(θ_i - θ_j)
        self.topological_energy = []       # TE = -strength * |Z| * cos(φ_sweep - arg(Z))
        self.total_energy = []
        self.power_dissipation = []        # Rate of energy change
        self.topological_power = []        # Power going into topological drive

    def kuramoto_order_parameter(self):
        """Compute r and Z."""
        Z = np.mean(np.exp(1j * self.theta))
        return np.abs(Z), Z

    def compute_kinetic_energy(self, dtheta):
        """
        Kinetic energy of the oscillator ensemble.
        KE ≈ (1/2) * Σ (dθ/dt)²
        """
        return 0.5 * np.sum(dtheta**2)

    def compute_coupling_energy(self):
        """
        Coupling energy from pairwise interactions.
        CE = -(K/N) * Σ cos(θ_i - θ_j)
        """
        theta_diff = self.theta[:, np.newaxis] - self.theta[np.newaxis, :]
        coupling_matrix = np.cos(theta_diff)
        return -(self.K / self.N) * np.sum(coupling_matrix)

    def compute_topological_energy(self, phi_sweep, r, Z):
        """
        Energy from topological phase drive.
        TE = -drive_strength * |Z| * cos(φ_sweep - arg(Z))
        This represents the external field coupling to the order parameter.
        """
        drive_strength = 0.3
        phase_misalignment = phi_sweep - np.angle(Z)
        return -drive_strength * r * np.cos(phase_misalignment)

    def step(self, phi_sweep):
        """Execute one step with full energy tracking."""
        r, Z = self.kuramoto_order_parameter()

        # Kuramoto coupling
        theta_diff = self.theta[:, np.newaxis] - self.theta[np.newaxis, :]
        coupling = (self.K / self.N) * np.sum(np.sin(theta_diff), axis=1)

        # Topological drive
        external_drive = 0.3 * np.sin(phi_sweep - self.theta)

        # Phase derivatives
        dtheta = self.omega_nat + coupling + external_drive

        # ===== Energy Computation =====
        KE = self.compute_kinetic_energy(dtheta)
        CE = self.compute_coupling_energy()
        TE = self.compute_topological_energy(phi_sweep, r, Z)
        total_E = KE + CE + TE

        # Store energy values
        self.kinetic_energy.append(KE)
        self.coupling_energy.append(CE)
        self.topological_energy.append(TE)
        self.total_energy.append(total_E)

        # Update phases
        self.theta += dtheta * self.dt
        self.theta = np.mod(self.theta, 2*np.pi)

        return dtheta, r, Z

    def run_simulation(self, verbose=True):
        """Run complete simulation with energy tracking."""
        if verbose:
            print("\n" + "="*70)
            print("Kuramoto Energy & Topological Transition Tracking")
            print("="*70)
            print(f"Configuration:")
            print(f"  Oscillators: {self.N}")
            print(f"  Fixed Coupling K: {self.K:.3f}")
            print(f"  Phase cycles: {self.phase_cycles}")
            print(f"  Sweep duration: {self.sweep_duration:.1f}")
            print("="*70 + "\n")

        for step in range(self.steps):
            t = step * self.dt
            phi_sweep = self.phi_sweep_t[step]

            dtheta, r, Z = self.step(phi_sweep)

            self.t_vals.append(t)
            self.r_vals.append(r)
            self.phi_sweep_vals.append(phi_sweep)
            self.Z_vals.append(Z)

            if verbose and step % max(1, self.steps // 10) == 0:
                KE = self.kinetic_energy[-1]
                CE = self.coupling_energy[-1]
                TE = self.topological_energy[-1]
                E_total = self.total_energy[-1]
                phase_pct = (step / self.steps) * 100
                print(f"Step {step:6d} | t={t:6.1f} | r={r:.4f} | "
                      f"E_tot={E_total:8.3f} | KE={KE:6.3f} | CE={CE:7.3f}")

        # Compute power dissipation
        self.compute_power_dissipation()

        if verbose:
            print("\n" + "="*70)
            print("Simulation Complete")
            print("="*70 + "\n")

    def compute_power_dissipation(self):
        """Compute power (dE/dt) from energy time series."""
        E_array = np.array(self.total_energy)
        # Power = dE/dt ≈ ΔE/Δt
        power = np.gradient(E_array) / self.dt
        self.power_dissipation = power.tolist()

        # Topological power (magnitude of coupling to external drive)
        phi_sweep_array = np.array(self.phi_sweep_vals)
        Z_array = np.array(self.Z_vals)
        r_array = np.array(self.r_vals)

        for i, (phi_s, Z, r) in enumerate(zip(phi_sweep_array, Z_array, r_array)):
            phase_misalignment = phi_s - np.angle(Z)
            # Power into topological drive
            topo_power = 0.3 * r * np.sin(phase_misalignment) * np.gradient(phi_sweep_array)[i] / self.dt
            self.topological_power.append(topo_power)

    def analyze_topological_structure(self):
        """Extract topological properties."""
        t_array = np.array(self.t_vals)
        Z_array = np.array(self.Z_vals)
        omega_bar_array = np.ones_like(t_array) * np.mean(self.omega_nat)

        return stroboscopic_subtraction_filter(t_array, Z_array, omega_bar_array)


def visualize_energy_transition(sim, topo_results):
    """Create comprehensive energy analysis visualization."""
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    t_array = np.array(sim.t_vals)
    r_array = np.array(sim.r_vals)
    phi_sweep = np.array(sim.phi_sweep_vals)
    KE = np.array(sim.kinetic_energy)
    CE = np.array(sim.coupling_energy)
    TE = np.array(sim.topological_energy)
    E_total = np.array(sim.total_energy)
    power = np.array(sim.power_dissipation)

    fig.suptitle(
        'Kuramoto Energy & Topological Transition Analysis\n'
        'Tracking energetics through Berry phase accumulation',
        fontsize=16, fontweight='bold'
    )

    # ===== Row 1: Phase & Synchronization =====
    ax = fig.add_subplot(gs[0, 0])
    ax.plot(t_array, phi_sweep, 'g-', linewidth=2.5, label='φ_sweep(t)')
    ax.fill_between(t_array, 0, phi_sweep, alpha=0.1, color='green')
    ax.set_ylabel('Topological Phase (rad)', fontsize=10, fontweight='bold')
    ax.set_title('Topological Drive', fontsize=10, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    ax = fig.add_subplot(gs[0, 1])
    ax.plot(t_array, r_array, 'b-', linewidth=2.5, label='Order Parameter r(t)')
    ax.fill_between(t_array, 0, r_array, alpha=0.15, color='blue')
    ax.axhline(0.85, color='r', linestyle='--', alpha=0.5, label='Critical threshold')
    ax.set_ylabel('r(t)', fontsize=10, fontweight='bold')
    ax.set_title('Synchronization State', fontsize=10, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_ylim([0, 1.1])

    ax = fig.add_subplot(gs[0, 2])
    Z_array = np.array(sim.Z_vals)
    phase_Z = np.angle(Z_array)
    ax.plot(t_array, phase_Z, 'orange', linewidth=2, label='arg(Z)')
    ax.plot(t_array, phi_sweep, 'g--', linewidth=1, alpha=0.5, label='φ_sweep')
    ax.set_ylabel('Phase (rad)', fontsize=10, fontweight='bold')
    ax.set_title('Order Parameter Phase Tracking', fontsize=10, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # ===== Row 2: Energy Components =====
    ax = fig.add_subplot(gs[1, 0])
    ax.plot(t_array, KE, 'r-', linewidth=2, label='Kinetic Energy', alpha=0.8)
    ax.fill_between(t_array, 0, KE, alpha=0.15, color='red')
    ax.set_ylabel('KE (a.u.)', fontsize=10, fontweight='bold')
    ax.set_title('Kinetic Energy Evolution', fontsize=10, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    ax = fig.add_subplot(gs[1, 1])
    ax.plot(t_array, CE, 'b-', linewidth=2, label='Coupling Energy', alpha=0.8)
    ax.fill_between(t_array, 0, CE, alpha=0.15, color='blue')
    ax.set_ylabel('CE (a.u.)', fontsize=10, fontweight='bold')
    ax.set_title('Coupling Energy Evolution', fontsize=10, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    ax = fig.add_subplot(gs[1, 2])
    ax.plot(t_array, TE, 'purple', linewidth=2, label='Topological Energy', alpha=0.8)
    ax.fill_between(t_array, 0, TE, alpha=0.15, color='purple')
    ax.set_ylabel('TE (a.u.)', fontsize=10, fontweight='bold')
    ax.set_title('Topological Drive Energy', fontsize=10, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    # ===== Row 3: Total Energy & Power =====
    ax = fig.add_subplot(gs[2, 0:2])
    ax.plot(t_array, E_total, 'k-', linewidth=2.5, label='Total Energy')
    ax.fill_between(t_array, 0, E_total, alpha=0.1, color='black')

    # Mark transitions (where |dr/dt| is large)
    dr_dt = np.gradient(r_array)
    transition_indices = np.where(np.abs(dr_dt) > np.mean(np.abs(dr_dt)))[0]
    for idx in transition_indices[::len(transition_indices)//5]:  # Sample every 5th
        ax.axvline(t_array[idx], color='red', linestyle=':', alpha=0.3, linewidth=0.8)

    ax.set_xlabel('Time', fontsize=10, fontweight='bold')
    ax.set_ylabel('Total Energy (a.u.)', fontsize=10, fontweight='bold')
    ax.set_title('Total Energy (KE + CE + TE)', fontsize=10, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    ax = fig.add_subplot(gs[2, 2])
    ax.plot(t_array, power, 'orange', linewidth=2, label='Power dE/dt')
    ax.axhline(0, color='k', linestyle='-', alpha=0.3, linewidth=0.5)
    ax.fill_between(t_array, 0, power, where=(power>0), alpha=0.2, color='red', label='Power in')
    ax.fill_between(t_array, 0, power, where=(power<0), alpha=0.2, color='blue', label='Power out')
    ax.set_xlabel('Time', fontsize=10, fontweight='bold')
    ax.set_ylabel('Power (dE/dt)', fontsize=10, fontweight='bold')
    ax.set_title('Energy Dissipation Rate', fontsize=10, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    return fig


def visualize_energy_summary(sim, topo_results):
    """Create energy summary statistics."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Energy Statistics & Topological Metrics', fontsize=14, fontweight='bold')

    t_array = np.array(sim.t_vals)
    r_array = np.array(sim.r_vals)
    KE = np.array(sim.kinetic_energy)
    CE = np.array(sim.coupling_energy)
    TE = np.array(sim.topological_energy)
    E_total = np.array(sim.total_energy)

    # Panel 1: Energy breakdown pie chart
    ax = axes[0, 0]
    mean_KE = np.mean(np.abs(KE))
    mean_CE = np.mean(np.abs(CE))
    mean_TE = np.mean(np.abs(TE))
    total_mag = mean_KE + mean_CE + mean_TE

    sizes = [mean_KE, mean_CE, mean_TE]
    labels = [f'KE\n({mean_KE/total_mag*100:.1f}%)',
              f'CE\n({mean_CE/total_mag*100:.1f}%)',
              f'TE\n({mean_TE/total_mag*100:.1f}%)']
    colors = ['red', 'blue', 'purple']

    ax.pie(sizes, labels=labels, colors=colors, autopct='', startangle=90)
    ax.set_title('Mean Energy Component Breakdown', fontsize=11, fontweight='bold')

    # Panel 2: Energy correlations
    ax = axes[0, 1]
    correlation_data = {
        'r vs E_tot': np.corrcoef(r_array, E_total)[0, 1],
        'r vs KE': np.corrcoef(r_array, KE)[0, 1],
        'r vs CE': np.corrcoef(r_array, CE)[0, 1],
        'r vs TE': np.corrcoef(r_array, TE)[0, 1],
    }

    corr_names = list(correlation_data.keys())
    corr_values = list(correlation_data.values())
    colors_corr = ['green' if v > 0 else 'red' for v in corr_values]

    bars = ax.barh(corr_names, corr_values, color=colors_corr, alpha=0.6, edgecolor='black')
    ax.axvline(0, color='k', linestyle='-', linewidth=0.5)
    ax.set_xlabel('Correlation Coefficient', fontsize=10, fontweight='bold')
    ax.set_title('Synchronization vs Energy Correlations', fontsize=11, fontweight='bold')
    ax.set_xlim([-1, 1])
    ax.grid(True, alpha=0.3, axis='x')

    for bar, val in zip(bars, corr_values):
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2,
               f' {val:.3f}', ha='left' if val > 0 else 'right', va='center', fontsize=9)

    # Panel 3: Energy landscape during transition
    ax = axes[1, 0]
    r_sorted_indices = np.argsort(r_array)
    r_sorted = r_array[r_sorted_indices]
    E_sorted = E_total[r_sorted_indices]

    ax.scatter(r_sorted, E_sorted, c=t_array[r_sorted_indices], cmap='viridis', s=20, alpha=0.6)
    ax.set_xlabel('Order Parameter r', fontsize=10, fontweight='bold')
    ax.set_ylabel('Total Energy', fontsize=10, fontweight='bold')
    ax.set_title('Energy vs Synchronization (Colored by time)', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Panel 4: Topological metrics summary
    ax = axes[1, 1]
    ax.axis('off')

    summary_text = f"""
    ENERGY & TOPOLOGICAL SUMMARY
    ════════════════════════════════════════

    Energy Statistics:
      • Mean KE: {np.mean(KE):.4f}
      • Mean CE: {np.mean(CE):.4f}
      • Mean TE: {np.mean(TE):.4f}
      • Mean Total E: {np.mean(E_total):.4f}
      • Max Total E: {np.max(E_total):.4f}
      • Min Total E: {np.min(E_total):.4f}

    Synchronization:
      • Mean r: {np.mean(r_array):.4f}
      • Peak r: {np.max(r_array):.4f}
      • Final r: {r_array[-1]:.4f}

    Topological Winding:
      • ν_geom: {topo_results['winding_nu']:.6f}
      • Rounded: {round(topo_results['winding_nu']):.0f}
      • Δφ_geom: {topo_results['delta_phi_geom']:.6f} rad

    Energy per Winding:
      • E/ν: {np.mean(E_total) / abs(topo_results['winding_nu']) if topo_results['winding_nu'] != 0 else 0:.4f}
      • Peak E/ν: {np.max(E_total) / abs(topo_results['winding_nu']) if topo_results['winding_nu'] != 0 else 0:.4f}

    Dissipation:
      • Total Power out: {np.sum(np.minimum(np.array(sim.power_dissipation), 0)):.4f}
      • Peak Power: {np.max(np.abs(sim.power_dissipation)):.4f}
      • Mean |Power|: {np.mean(np.abs(sim.power_dissipation)):.4f}
    """

    ax.text(0.05, 0.95, summary_text, transform=ax.transAxes,
           fontsize=9, verticalalignment='top', family='monospace',
           bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7))

    plt.tight_layout()
    return fig


if __name__ == "__main__":
    # Run simulation
    sim = KuramotoEnergyTracker(N=256, K=1.2, phase_cycles=3, sweep_duration=300.0)
    sim.run_simulation(verbose=True)

    # Analyze topology
    topo_results = sim.analyze_topological_structure()

    # Print summary
    print("\n" + "="*70)
    print("ENERGY & TOPOLOGICAL TRANSITION ANALYSIS")
    print("="*70)
    print(f"\nEnergy Statistics:")
    print(f"  Mean Kinetic Energy: {np.mean(sim.kinetic_energy):.6f}")
    print(f"  Mean Coupling Energy: {np.mean(sim.coupling_energy):.6f}")
    print(f"  Mean Topological Energy: {np.mean(sim.topological_energy):.6f}")
    print(f"  Mean Total Energy: {np.mean(sim.total_energy):.6f}")
    print(f"  Total Energy Range: [{np.min(sim.total_energy):.6f}, {np.max(sim.total_energy):.6f}]")

    print(f"\nTopological Properties:")
    print(f"  Geometric Winding ν: {topo_results['winding_nu']:.6f}")
    print(f"  Quantized Charge: {round(topo_results['winding_nu']):.0f}")
    print(f"  Total Geometric Phase: {topo_results['delta_phi_geom']:.6f} rad")

    print(f"\nSynchronization:")
    print(f"  Mean Order Parameter: {np.mean(sim.r_vals):.4f}")
    print(f"  Peak Order Parameter: {np.max(sim.r_vals):.4f}")
    print(f"  Final Order Parameter: {sim.r_vals[-1]:.4f}")

    print(f"\nEnergy per Topological Winding:")
    if topo_results['winding_nu'] != 0:
        print(f"  Mean E/ν: {np.mean(sim.total_energy) / abs(topo_results['winding_nu']):.6f}")
        print(f"  Max E/ν: {np.max(sim.total_energy) / abs(topo_results['winding_nu']):.6f}")

    print("="*70 + "\n")

    # Visualize
    fig1 = visualize_energy_transition(sim, topo_results)
    plt.savefig('/home/user/natural-emergence/energy_topological_transition.png', dpi=150, bbox_inches='tight')
    print("✓ Main visualization saved to energy_topological_transition.png\n")

    fig2 = visualize_energy_summary(sim, topo_results)
    plt.savefig('/home/user/natural-emergence/energy_topological_summary.png', dpi=150, bbox_inches='tight')
    print("✓ Summary visualization saved to energy_topological_summary.png\n")

    # Save results
    output = {
        "experiment": "Energy tracking through topological phase transition",
        "config": {
            "oscillators": sim.N,
            "coupling_K": sim.K,
            "phase_cycles": sim.phase_cycles,
            "sweep_duration": sim.sweep_duration,
            "time_steps": sim.steps
        },
        "energy_statistics": {
            "mean_kinetic_energy": float(np.mean(sim.kinetic_energy)),
            "mean_coupling_energy": float(np.mean(sim.coupling_energy)),
            "mean_topological_energy": float(np.mean(sim.topological_energy)),
            "mean_total_energy": float(np.mean(sim.total_energy)),
            "max_total_energy": float(np.max(sim.total_energy)),
            "min_total_energy": float(np.min(sim.total_energy))
        },
        "topological_metrics": {
            "winding_number": float(topo_results['winding_nu']),
            "quantized_charge": int(round(topo_results['winding_nu'])),
            "total_geometric_phase": float(topo_results['delta_phi_geom'])
        },
        "synchronization": {
            "mean_order_parameter": float(np.mean(sim.r_vals)),
            "max_order_parameter": float(np.max(sim.r_vals)),
            "final_order_parameter": float(sim.r_vals[-1])
        },
        "efficiency": {
            "energy_per_winding": float(np.mean(sim.total_energy) / abs(topo_results['winding_nu']) if topo_results['winding_nu'] != 0 else 0),
            "peak_energy_per_winding": float(np.max(sim.total_energy) / abs(topo_results['winding_nu']) if topo_results['winding_nu'] != 0 else 0)
        }
    }

    with open('/home/user/natural-emergence/energy_topological_results.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("✓ Results saved to energy_topological_results.json\n")

    plt.show()
