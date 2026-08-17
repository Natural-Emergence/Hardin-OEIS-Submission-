#!/usr/bin/env python3
"""
Example usage of the Kuramoto-MaxCaliber Unified Field Simulator

Demonstrates:
1. Basic simulation execution
2. Real-time metric tracking
3. System rules application
4. Visualization generation
"""

from kuramoto_maxcaliber_simulator import (
    KuramotoMaxCaliberSimulator,
    SimulationVisualizer,
    SystemLevelRules
)
import matplotlib.pyplot as plt


def example_1_basic_simulation():
    """Run a basic simulation with default parameters."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Simulation")
    print("="*70)

    sim = KuramotoMaxCaliberSimulator(
        N=128,        # 128 processing fibers
        D=512,        # 512-dimensional state space
        duration=100, # 100 time units
        dt=0.01       # 0.01 time step resolution
    )

    sim.run(verbose=True)
    return sim


def example_2_analyze_metrics(sim):
    """Analyze simulation metrics in detail."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Detailed Metric Analysis")
    print("="*70)

    metrics = sim.metrics

    print(f"\nOrder Parameter Statistics:")
    print(f"  Mean:     {sum(metrics.order_parameter)/len(metrics.order_parameter):.4f}")
    print(f"  Max:      {max(metrics.order_parameter):.4f}")
    print(f"  Min:      {min(metrics.order_parameter):.4f}")
    print(f"  Final:    {metrics.order_parameter[-1]:.4f}")

    print(f"\nCoupling Strength Statistics:")
    print(f"  Mean:     {sum(metrics.coupling_strength)/len(metrics.coupling_strength):.4f}")
    print(f"  Max:      {max(metrics.coupling_strength):.4f}")
    print(f"  Min:      {min(metrics.coupling_strength):.4f}")
    print(f"  Final:    {metrics.coupling_strength[-1]:.4f}")

    print(f"\nCurvature Statistics:")
    print(f"  Initial:  {metrics.curvature[0]:.4f}")
    print(f"  Final:    {metrics.curvature[-1]:.4f}")
    print(f"  Decay %:  {100*(1-metrics.curvature[-1]/metrics.curvature[0]):.2f}%")

    print(f"\nPath Entropy Statistics:")
    print(f"  Initial:  {metrics.path_entropy[0]:.4f}×")
    print(f"  Final:    {metrics.path_entropy[-1]:.4f}×")
    print(f"  Growth %: {100*(metrics.path_entropy[-1]-metrics.path_entropy[0])/0.33:.2f}%")

    print(f"\nPhase Variance Statistics:")
    print(f"  Initial:  {metrics.phase_variance[0]:.4f}")
    print(f"  Final:    {metrics.phase_variance[-1]:.4f}")
    print(f"  Change:   {100*(metrics.phase_variance[0]-metrics.phase_variance[-1])/metrics.phase_variance[0]:.2f}%")

    print(f"\nInformation Flow Statistics:")
    print(f"  Mean:     {sum(metrics.information_flow)/len(metrics.information_flow):.4f}")
    print(f"  Max:      {max(metrics.information_flow):.4f}")
    print(f"  Peak Time: t={metrics.time_points[metrics.information_flow.index(max(metrics.information_flow))]:.2f}")


def example_3_system_rules(sim):
    """Demonstrate the three core system rules."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Production System Rules")
    print("="*70)

    r_final = sim.metrics.order_parameter[-1]
    phase_var = sim.metrics.phase_variance[-1]
    curv_final = sim.metrics.curvature[-1]
    k_final = sim.metrics.coupling_strength[-1]

    # Rule 1: Thread scheduling
    print("\nRule 1: Phase-Aware Thread Scheduling")
    print("-" * 70)
    thread_config = SystemLevelRules.phase_aware_thread_scheduling(r_final, phase_var)
    print(f"  Current state: r={r_final:.3f}, phase_variance={phase_var:.3f}")
    print(f"  Recommendation: {thread_config['action']}")
    print(f"  Throttle factor: {thread_config['throttle_factor']:.2f}")
    print(f"  Recommended threads: {thread_config['recommended_threads']}")

    # Rule 2: Memory caching
    print("\nRule 2: Volatile Memory Caching Matrix")
    print("-" * 70)
    memory_config = SystemLevelRules.volatile_memory_caching_matrix(curv_final)
    print(f"  Current curvature: {curv_final:.3f}")
    print(f"  Path multiplier: {memory_config['path_multiplier']:.3f}×")
    print(f"  Available cache: {memory_config['available_cache_pools_mb']:.1f} MB")
    print(f"  Memory dimensions: {memory_config['memory_dimensions']}D")
    print(f"  Thermal footprint: {memory_config['thermal_footprint_percent']}%")

    # Rule 3: Checkpointing
    print("\nRule 3: Entropy-Based Checkpointing")
    print("-" * 70)
    checkpoint_config = SystemLevelRules.entropy_based_checkpointing(r_final, k_final)
    print(f"  Current coupling: κ={k_final:.3f}")
    print(f"  Nearest boundary: {checkpoint_config['nearest_boundary']:.3f}")
    print(f"  Should checkpoint: {checkpoint_config['should_checkpoint']}")
    print(f"  Checkpoint boundaries: {checkpoint_config['checkpoint_boundaries']}")
    if checkpoint_config['should_checkpoint']:
        print(f"  → Perform disk backup now")
    else:
        print(f"  → Stream to volatile buffer only")


def example_4_visualization(sim):
    """Generate and display visualizations."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Publication-Quality Visualizations")
    print("="*70)

    visualizer = SimulationVisualizer(sim)

    print("\nGenerating comprehensive analysis plot...")
    fig1 = visualizer.create_comprehensive_plot()
    fig1.savefig('example_comprehensive.png', dpi=300, bbox_inches='tight')
    print("  → Saved: example_comprehensive.png")

    print("\nGenerating trajectory analysis plot...")
    fig2 = visualizer.create_trajectory_analysis_plot()
    fig2.savefig('example_trajectories.png', dpi=300, bbox_inches='tight')
    print("  → Saved: example_trajectories.png")

    print("\nVisualizations ready for publication/presentation.")


def example_5_custom_configuration():
    """Run simulation with custom parameters."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Custom Configuration")
    print("="*70)

    print("\nRunning with custom parameters:")
    print("  - Fewer fibers (N=64) for faster execution")
    print("  - Extended duration (200 time units)")

    sim_custom = KuramotoMaxCaliberSimulator(
        N=64,
        D=512,
        duration=200,
        dt=0.02  # Larger time step for speed
    )

    # Manually run a subset
    print("\nExecuting first 500 steps...")
    for step in range(500):
        sim_custom.step(step * sim_custom.dt)

    r = sim_custom.metrics.order_parameter[-1]
    c = sim_custom.metrics.curvature[-1]
    print(f"\nAfter 500 steps:")
    print(f"  Order parameter: {r:.4f}")
    print(f"  Curvature: {c:.4f}")

    return sim_custom


def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("Kuramoto-MaxCaliber Unified Field Simulator - Usage Examples")
    print("="*80)

    # Example 1: Run basic simulation
    sim = example_1_basic_simulation()

    # Example 2: Analyze metrics
    example_2_analyze_metrics(sim)

    # Example 3: Show system rules
    example_3_system_rules(sim)

    # Example 4: Create visualizations
    example_4_visualization(sim)

    # Example 5: Custom configuration
    sim_custom = example_5_custom_configuration()

    print("\n" + "="*80)
    print("Examples completed successfully!")
    print("="*80)
    print("\nGenerated files:")
    print("  - example_comprehensive.png")
    print("  - example_trajectories.png")
    print("  - kuramoto_maxcaliber_comprehensive.png")
    print("  - kuramoto_maxcaliber_trajectories.png")
    print("  - simulation_metrics.json")
    print("\nView the visualizations to understand system behavior.")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
