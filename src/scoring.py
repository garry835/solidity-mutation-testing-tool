"""Calculates mutation scores and experimental metrics."""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from src.mutant_model import Mutant, MutationStatus


@dataclass
class OperatorScore:
    """Mutation score metrics broken down by individual operator."""
    operator_name: str
    total_mutants: int = 0
    killed: int = 0
    survived: int = 0
    invalid: int = 0
    equivalent: int = 0
    timeout: int = 0
    unresolved: int = 0
    mutation_score: float = 0.0

    def compute_score(self) -> float:
        """Calculate mutation score: K / (M - I - E) * 100."""
        denominator = self.total_mutants - self.invalid - self.equivalent
        if denominator <= 0:
            self.mutation_score = 0.0
        else:
            self.mutation_score = round((self.killed / denominator) * 100.0, 2)
        return self.mutation_score


@dataclass
class CampaignMetrics:
    """Comprehensive metrics for the entire mutation testing campaign."""
    total_candidates_discovered: int = 0
    total_candidates_rejected: int = 0
    rejection_reasons: Dict[str, int] = field(default_factory=dict)

    total_mutants: int = 0
    killed: int = 0
    survived: int = 0
    invalid: int = 0
    equivalent: int = 0
    timeout: int = 0
    unresolved: int = 0

    mutation_score: float = 0.0
    compilation_success_rate: float = 0.0
    total_execution_time_seconds: float = 0.0
    average_execution_time_seconds: float = 0.0

    operator_scores: Dict[str, OperatorScore] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, any]:
        """Convert metrics to serializable dictionary."""
        d = asdict(self)
        d["operator_scores"] = {k: asdict(v) for k, v in self.operator_scores.items()}
        return d


class ScoringEngine:
    """Computes academic-grade mutation metrics and breakdown scores."""

    @staticmethod
    def calculate(
        mutants: List[Mutant],
        total_candidates: int,
        rejected_candidates: int,
        rejection_reasons: Optional[Dict[str, int]] = None
    ) -> CampaignMetrics:
        """Calculate overall and per-operator mutation metrics.

        Args:
            mutants: List of all evaluated mutants.
            total_candidates: Total eligible and considered candidates discovered.
            rejected_candidates: Total candidates discarded during filtering.
            rejection_reasons: Dict mapping rejection explanations to counts.

        Returns:
            CampaignMetrics containing all computed scores.
        """
        metrics = CampaignMetrics(
            total_candidates_discovered=total_candidates,
            total_candidates_rejected=rejected_candidates,
            rejection_reasons=rejection_reasons or {},
            total_mutants=len(mutants)
        )

        operator_map: Dict[str, OperatorScore] = {}
        total_time = 0.0
        compilation_successes = 0

        for m in mutants:
            op_name = m.operator_name
            if op_name not in operator_map:
                operator_map[op_name] = OperatorScore(operator_name=op_name)
            op = operator_map[op_name]
            op.total_mutants += 1

            total_time += m.execution_time_seconds
            if m.compilation_success:
                compilation_successes += 1

            if m.status == MutationStatus.KILLED:
                metrics.killed += 1
                op.killed += 1
            elif m.status == MutationStatus.SURVIVED:
                if m.suspected_equivalent:
                    metrics.equivalent += 1
                    op.equivalent += 1
                else:
                    metrics.survived += 1
                    op.survived += 1
            elif m.status == MutationStatus.INVALID:
                metrics.invalid += 1
                op.invalid += 1
            elif m.status == MutationStatus.EQUIVALENT:
                metrics.equivalent += 1
                op.equivalent += 1
            elif m.status == MutationStatus.TIMEOUT:
                metrics.timeout += 1
                op.timeout += 1
            elif m.status == MutationStatus.UNRESOLVED:
                metrics.unresolved += 1
                op.unresolved += 1

        # Calculate per-operator scores
        for op in operator_map.values():
            op.compute_score()
        metrics.operator_scores = operator_map

        # Overall Mutation Score: K / (M - I - E) * 100
        # Timeouts and Unresolved mutants are preserved in the denominator (M - I - E),
        # ensuring that test failures due to timeouts/environmental bugs are not concealed.
        effective_denominator = (
            metrics.total_mutants - metrics.invalid - metrics.equivalent
        )
        if effective_denominator <= 0:
            metrics.mutation_score = 0.0
        else:
            metrics.mutation_score = round(
                (metrics.killed / effective_denominator) * 100.0, 2
            )

        # Compilation Success Rate
        if metrics.total_mutants > 0:
            metrics.compilation_success_rate = round(
                (compilation_successes / metrics.total_mutants) * 100.0, 2
            )
            metrics.average_execution_time_seconds = round(
                total_time / metrics.total_mutants, 3
            )
        else:
            metrics.compilation_success_rate = 0.0
            metrics.average_execution_time_seconds = 0.0

        metrics.total_execution_time_seconds = round(total_time, 2)
        return metrics
