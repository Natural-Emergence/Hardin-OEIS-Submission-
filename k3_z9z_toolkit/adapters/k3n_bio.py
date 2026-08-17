"""
K3N-BIO mRNA Vaccine Optimization as K₃ × Z/9Z System

Adapts codon optimization to universal topology.

K₃ Operations:
  1. Context scoring: evaluate 9-nt codon windows (exploration)
  2. Transitions: generate synonymous codon substitutions (sampling)
  3. Partitioning: organize into FT10-style buckets (refinement)

Z/9Z Structure:
  - Explicit 9-nucleotide context windows
  - 9 codon positions in local context
  - Codon × position × score = 3 × 3 × 1

Z₃ Phases:
  - Initialization: random starting sequence
  - Exploration: codon variations, high diversity
  - Refinement: top-k selection
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from collections import Counter

from k3_z9z_toolkit.core.topology import K3Z9ZBlueprint, K3Z9ZSystem


# Minimal genetic code for demo
CODON_TABLE = {
    'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
    'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
    'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
    'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W',
    'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',
    'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
    'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
    'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
    'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M',
    'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
    'AAT': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K',
    'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
    'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',
    'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
    'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
    'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G',
}

AA_TO_CODONS = {}
for codon, aa in CODON_TABLE.items():
    if aa not in AA_TO_CODONS:
        AA_TO_CODONS[aa] = []
    AA_TO_CODONS[aa].append(codon)

# Simplified tRNA availability (lower = faster)
RRT_SIMPLIFIED = {
    'TTT': 1.48, 'TTC': 0.75, 'CTC': 0.70, 'CTG': 0.90,
    'TAT': 1.22, 'TAC': 0.82, 'TGT': 1.18, 'TGC': 0.85,
    'CTT': 1.28, 'CTA': 1.65, 'CCT': 1.02, 'CCC': 0.92,
    'CAT': 1.15, 'CAC': 0.92, 'CAA': 1.35, 'CAG': 0.98,
    'CGT': 0.95, 'CGC': 0.78, 'CGA': 1.58, 'CGG': 1.08,
    'ATT': 1.22, 'ATC': 0.82, 'ATA': 1.72, 'ATG': 1.15,
    'ACT': 1.08, 'ACC': 0.95, 'ACA': 1.25, 'ACG': 0.98,
    'AAT': 1.32, 'AAC': 0.88, 'AAA': 1.28, 'AAG': 1.05,
    'AGT': 1.18, 'AGC': 0.92, 'AGA': 1.62, 'AGG': 1.15,
    'GTT': 1.15, 'GTC': 0.88, 'GTA': 1.42, 'GTG': 1.02,
    'GCT': 1.08, 'GCC': 0.82, 'GCA': 1.32, 'GCG': 0.95,
    'GAT': 1.22, 'GAC': 0.92, 'GAA': 1.38, 'GAG': 1.08,
    'GGT': 1.02, 'GGC': 0.88, 'GGA': 1.35, 'GGG': 0.98,
    'TTA': 1.55, 'TTG': 0.95, 'TCA': 1.32, 'TCG': 0.82,
    'TCT': 1.12, 'TCC': 0.88, 'TAA': 2.10, 'TAG': 2.15,
    'TGA': 2.25, 'TGG': 1.05, 'CCC': 0.92, 'CCA': 1.28,
    'CCG': 0.95, 'AGA': 1.62, 'AAG': 1.05, 'AGC': 0.92
}


@dataclass
class mRNAState:
    """State of mRNA sequence optimization"""
    codons: List[str]               # Current sequence
    coherence_history: List[float] = field(default_factory=list)  # Track coherence scores
    best_codons: List[str] = None   # Best found
    best_coherence: float = 0.0     # Best score


class K3NBIOSystemAdapter(K3Z9ZBlueprint):
    """K3N-BIO mRNA optimizer as K₃ × Z/9Z"""

    def __init__(self, target_protein: str = "MFVFLVLLPL"):
        """
        Args:
            target_protein: Amino acid sequence to optimize for
        """
        self.target_protein = target_protein
        self.domain_name = "k3n_bio_codon_optimization"

    def _get_rrt(self, codon: str) -> float:
        """Get tRNA availability (RRT) for codon"""
        return RRT_SIMPLIFIED.get(codon, 1.2)

    def _score_context_window(self, codons: List[str], center_idx: int) -> float:
        """
        Score 9-nt context window around position center_idx

        K₃ concept: slow codons should be flanked by fast neighbors
        """
        if center_idx < 3 or center_idx >= len(codons) - 3:
            return 1.0

        # Extract window: 7 codons = 21 nucleotides ≈ 9-nt focus window
        window = codons[center_idx-3 : center_idx+4]
        window_rrt = [self._get_rrt(c) for c in window]

        # Coherence: slow center flanked by fast neighbors?
        center_rrt = window_rrt[3]
        neighbor_rrt = [window_rrt[2], window_rrt[4]]

        if np.mean(neighbor_rrt) < 0.01:
            return 0.0

        speed_ratio = center_rrt / (np.mean(neighbor_rrt) + 0.01)
        coherence = min(speed_ratio, 2.0) / 2.0
        return float(coherence)

    def init_state(self) -> mRNAState:
        """Initialize with random codons"""
        codons = []
        for aa in self.target_protein:
            candidates = AA_TO_CODONS.get(aa, ['TTT'])
            codons.append(np.random.choice(candidates))
        return mRNAState(codons=codons, best_codons=codons.copy(), best_coherence=0.0)

    def operation_1(self, state: mRNAState) -> List[List[str]]:
        """
        Context scoring: evaluate all 9-nt windows

        Returns: list of suggested codon variations
        """
        suggestions = []

        # For each position, suggest faster alternative if possible
        for i, codon in enumerate(state.codons):
            aa = CODON_TABLE[codon]
            alternatives = AA_TO_CODONS.get(aa, [codon])

            # Pick top 3 alternatives by speed
            alts_by_speed = sorted(alternatives, key=lambda c: self._get_rrt(c))[:3]

            suggestions.append(alts_by_speed)

        return suggestions

    def operation_2(self, state: mRNAState, r1: List[List[str]]) -> Tuple[float, List[str]]:
        """
        Transitions: generate codon variations and score them

        Args:
            state: Current state
            r1: Suggestions from operation_1

        Returns: (best_coherence_from_suggestions, best_variant_codons)
        """
        best_score = 0.0
        best_variant = state.codons.copy()

        # Try substitutions at random positions
        for pos in np.random.choice(len(state.codons), size=min(3, len(state.codons)), replace=False):
            # Try each suggestion
            for alt_codon in r1[pos]:
                variant = state.codons.copy()
                variant[pos] = alt_codon

                # Score entire sequence
                scores = [self._score_context_window(variant, i) for i in range(len(variant))]
                mean_score = np.mean(scores) if scores else 0.0

                if mean_score > best_score:
                    best_score = mean_score
                    best_variant = variant

        return best_score, best_variant

    def operation_3(self, state: mRNAState, r1: List[List[str]], r2: Tuple) -> mRNAState:
        """
        Partitioning: select best variant and update state

        Args:
            state: Current state
            r1: Suggestions from operation_1
            r2: (best_score, best_variant) from operation_2

        Returns: Updated state
        """
        score, variant = r2

        state.codons = variant
        state.coherence_history.append(score)

        # Track best
        if score > state.best_coherence:
            state.best_coherence = score
            state.best_codons = variant.copy()

        return state

    def control_metric(self, state: mRNAState) -> float:
        """
        Measure: mean coherence across all 9-nt windows

        Returns: score in [0, 1]
        """
        scores = [self._score_context_window(state.codons, i) for i in range(len(state.codons))]
        return float(np.mean(scores)) if scores else 0.0

    def validate(self, state: mRNAState) -> Dict[str, float]:
        """
        Validate optimization progress

        Returns metrics
        """
        current_scores = [self._score_context_window(state.codons, i) for i in range(len(state.codons))]
        best_scores = [self._score_context_window(state.best_codons, i) for i in range(len(state.best_codons))]

        return {
            'current_coherence': float(np.mean(current_scores)),
            'best_coherence': float(state.best_coherence),
            'coherence_improvement': float(state.best_coherence - np.mean(current_scores)),
            'avg_rrt': float(np.mean([self._get_rrt(c) for c in state.best_codons])),
            'iterations': len(state.coherence_history)
        }


def test_k3n_bio():
    """Test K3N-BIO adapter"""
    print("=" * 70)
    print("Testing K3N-BIO Codon Optimizer as K₃ × Z/9Z")
    print("=" * 70)

    # Build system
    adapter = K3NBIOSystemAdapter(target_protein="MFVFLVLL")
    system = adapter.build_system(threshold=0.6)

    # Initialize
    state = adapter.init_state()
    print(f"\nInitial coherence: {adapter.control_metric(state):.4f}")

    # Run optimization
    print(f"Running 100 iterations...")
    state, history = system.run(state, 100)

    # Analyze
    controls = [h['control'] for h in history]
    print(f"Final coherence: {controls[-1]:.4f}")
    print(f"Best coherence: {state.best_coherence:.4f}")
    print(f"Convergence rate (coherence ≥ 0.6): {system.convergence_rate():.2%}")

    # Validation
    val = adapter.validate(state)
    print(f"\nValidation:")
    for k, v in val.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")

    # Sequence comparison
    print(f"\nSequence comparison:")
    print(f"  Initial: {''.join(state.codons)}")
    print(f"  Best:    {''.join(state.best_codons)}")

    print("\n✓ Test complete\n")


if __name__ == "__main__":
    test_k3n_bio()
