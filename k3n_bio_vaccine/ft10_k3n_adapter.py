#!/usr/bin/env python3
"""
FT10 Frontier Search Adapter for K3N-BIO Vaccine Optimization

Integrates ft10_partitioned with mRNA vaccine codon optimization.
Uses FT10's external partitioning to exhaustively search large
sequence spaces without RAM ceiling.
"""

from pathlib import Path
from typing import List, Iterator, Tuple
import numpy as np

from k3n_bio_vaccine_optimizer import (
    mRNASequence, mRNATransitions, CodonContextEngine, CODON_TABLE
)


def sequence_to_u64(codons: List[str]) -> int:
    """Convert codon sequence to 64-bit hash for FT10 partitioning."""
    sorted_codons = sorted(CODON_TABLE.keys())
    codon_to_idx = {c: i for i, c in enumerate(sorted_codons)}

    hash_val = 0
    for i, codon in enumerate(codons[:10]):
        idx = codon_to_idx[codon]
        hash_val |= (idx << (6 * i))

    length_bits = min(len(codons), 15)
    hash_val |= (length_bits << 60)

    return hash_val & ((1 << 64) - 1)


class VaccineSequencePartitioner:
    """Partition vaccine codon sequences for FT10 frontier search."""

    def __init__(self, root: Path, bucket_bits: int = 8):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.bucket_bits = bucket_bits
        self.bucket_count = 1 << bucket_bits
        self.context_engine = CodonContextEngine()

    def hash_for_partition(self, codons: List[str]) -> int:
        return sequence_to_u64(codons)

    def partition_id(self, hash_val: int) -> int:
        return hash_val >> (64 - self.bucket_bits)

    def expand_frontier(self, current_sequences: List[mRNASequence]) -> Iterator[Tuple[mRNASequence, float]]:
        """Expand frontier: generate all successors and score."""
        transitions = mRNATransitions()
        seen_hashes = set()

        for seq in current_sequences:
            successors = transitions.next_states(seq)

            for succ in successors:
                h = self.hash_for_partition(succ.codons)

                if h in seen_hashes:
                    continue
                seen_hashes.add(h)

                coherence, _ = self.context_engine.score_sequence(succ.codons)
                yield succ, coherence

    def partition_frontier(self, frontier: List[mRNASequence]) -> dict:
        """Partition frontier into bucket files."""
        partitions = {i: [] for i in range(self.bucket_count)}

        for seq in frontier:
            h = self.hash_for_partition(seq.codons)
            bid = self.partition_id(h)
            partitions[bid].append(seq)

        return partitions

    def dedup_bucket(self, sequences: List[mRNASequence]) -> List[mRNASequence]:
        """Remove duplicate sequences from bucket."""
        seen = set()
        unique = []

        for seq in sequences:
            key = tuple(seq.codons)
            if key not in seen:
                seen.add(key)
                unique.append(seq)

        return unique


class FT10VaccineFrontier:
    """
    Main orchestrator: use FT10 partitioning to explore vaccine sequence space.
    
    Workflow:
    1. Start with initial sequence
    2. Expand: generate all codon variations
    3. Partition: split into buckets by sequence signature
    4. Deduplicate: keep unique sequences per bucket
    5. Score: compute coherence for each
    6. Recombine: select top-K for next frontier
    7. Repeat
    """

    def __init__(self, protein_sequence: str, work_dir: Path = Path("/tmp/ft10_vaccine"),
                 bucket_bits: int = 8):
        self.protein = protein_sequence
        self.work_dir = Path(work_dir)
        self.bucket_bits = bucket_bits
        self.partitioner = VaccineSequencePartitioner(self.work_dir, bucket_bits)
        self.context_engine = CodonContextEngine()

        self.frontier = [self._create_initial_sequence()]

    def _create_initial_sequence(self) -> mRNASequence:
        """Create initial codon sequence (common codons)."""
        from k3n_bio_vaccine_optimizer import AA_TO_CODONS

        codons = []
        for aa in self.protein:
            candidates = AA_TO_CODONS.get(aa, ['NNN'])
            rrt_scores = [self.context_engine.score_codon(c) for c in candidates]
            idx = np.argsort(rrt_scores)[len(rrt_scores) // 2]
            codons.append(candidates[idx])

        return mRNASequence(codons)

    def expand_one_layer(self, top_k: int = 50) -> dict:
        """Expand frontier by one layer using FT10 partitioning."""
        candidates = []
        for seq, score in self.partitioner.expand_frontier(self.frontier):
            candidates.append((seq, score))

        if not candidates:
            return {'error': 'no_candidates'}

        sequences = [c[0] for c in candidates]
        scores = [c[1] for c in candidates]

        partitions = self.partitioner.partition_frontier(sequences)

        all_unique = []
        for bid in range(self.partitioner.bucket_count):
            unique_in_bucket = self.partitioner.dedup_bucket(partitions[bid])
            all_unique.extend(unique_in_bucket)

        scored = []
        for seq in all_unique:
            _, metrics = self.context_engine.score_sequence(seq.codons)
            coherence = metrics['mean_coherence']
            scored.append((seq, coherence))

        scored.sort(key=lambda x: x[1], reverse=True)
        self.frontier = [s[0] for s in scored[:top_k]]

        scores = [s[1] for s in scored[:top_k]]

        return {
            'new_frontier_size': len(self.frontier),
            'best_score': float(max(scores)),
            'avg_score': float(np.mean(scores)),
            'total_candidates': len(candidates),
            'unique_sequences': len(all_unique),
        }

    def search(self, num_layers: int = 5, top_k: int = 50, verbose: bool = False) -> dict:
        """Run multi-layer frontier expansion."""
        if verbose:
            print(f"FT10 Vaccine Frontier Search")
            print(f"  Target protein: {self.protein}")

        history = []

        for layer in range(num_layers):
            result = self.expand_one_layer(top_k=top_k)

            if 'error' in result:
                if verbose:
                    print(f"Layer {layer}: {result['error']}")
                break

            history.append(result)

            if verbose:
                print(f"Layer {layer}: frontier={result['new_frontier_size']}, "
                      f"best={result['best_score']:.4f}")

        best_seq = self.frontier[0]
        best_score, best_metrics = self.context_engine.score_sequence(best_seq.codons)

        for seq in self.frontier[1:]:
            score, _ = self.context_engine.score_sequence(seq.codons)
            if score > best_score:
                best_seq = seq
                best_score = score

        return {
            'final_frontier': self.frontier,
            'best_sequence': best_seq,
            'best_score': best_score,
            'best_metrics': best_metrics,
            'layer_history': history,
        }


if __name__ == '__main__':
    spike_fragment = "MFVFLVLLPL"
    frontier = FT10VaccineFrontier(spike_fragment)
    print("K3N-BIO + FT10 Frontier Search initialized")
