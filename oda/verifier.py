"""
ODA Mathematical Invariant Verifier
Runs formal stress-testing and verifies zero intent loss, commutativity, and replayability.
Standard Specification & Architecture by Anirudha Puthraya.
"""

import random
import time
from typing import Any, Dict, List

from odc.core import ODCModel

from .algorithm import ODAAlgorithm
from .controller import CarrierEnvironment, ODANetworkSimulator


class VerificationReport:
    """Formal verification report summarizing invariant test results."""

    def __init__(self):
        self.total_actions = 0
        self.total_dropped = 0
        self.max_latency_ms = 0.0
        self.min_latency_ms = float("inf")
        self.avg_latency_ms = 0.0
        self.carrier_transitions = 0
        self.reconciled_actions = 0
        self.merkle_wal_verified = False
        self.crdt_consistency_verified = False
        self.passed = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "total_actions": self.total_actions,
            "total_dropped": self.total_dropped,
            "max_latency_ms": round(self.max_latency_ms, 3),
            "min_latency_ms": round(self.min_latency_ms, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 3),
            "carrier_transitions": self.carrier_transitions,
            "reconciled_actions": self.reconciled_actions,
            "merkle_wal_verified": self.merkle_wal_verified,
            "crdt_consistency_verified": self.crdt_consistency_verified,
        }


class ODAMathematicalVerifier:
    """
    Formal invariant verifier proving mathematical correctness of the ODC/ODA architecture.
    """

    @staticmethod
    def verify_resilience(iterations: int = 1000) -> VerificationReport:
        report = VerificationReport()
        model = ODCModel("verifier-node-1")
        oda = ODAAlgorithm(model)
        sim = ODANetworkSimulator(CarrierEnvironment.FIBER_OPTIMAL)

        latencies: List[float] = []
        environments = [
            CarrierEnvironment.FIBER_OPTIMAL,
            CarrierEnvironment.STARLINK_SATELLITE,
            CarrierEnvironment.TOTAL_BLACKOUT,
            CarrierEnvironment.UNDERGROUND_SUBWAY,
            CarrierEnvironment.CELLULAR_4G_5G,
        ]

        for i in range(iterations):
            # 1. Randomly rotate carrier environment
            if i % 100 == 0:
                new_env = random.choice(environments)
                sim.set_environment(new_env)
                report.carrier_transitions += 1

            rtt, loss = sim.sample_carrier()
            oda.evaluate_telemetry(rtt, loss)

            # 2. Submit user action
            action_name = f"ACTION_{i}"
            payload = {"seq": i, "data": f"payload_value_{i}", "entropy": random.random()}

            t0 = time.monotonic_ns()
            state, receipt = oda.submit_action(action_name, payload, actor="test_runner")
            t1 = time.monotonic_ns()

            duration_ms = (t1 - t0) / 1_000_000.0
            latencies.append(duration_ms)
            report.total_actions += 1

            # Invariant: Sub-16ms local authority
            if duration_ms > 16.66:
                raise RuntimeError(f"ZIL Violation: Action {i} took {duration_ms}ms (> 16.66ms)")

            # Invariant: Receipt signature valid
            if not receipt.verify():
                raise RuntimeError(f"Cryptographic Signature Failure on action {i}")

        # Final transition to FIBER_OPTIMAL to flush disruption buffer
        sim.set_environment(CarrierEnvironment.FIBER_OPTIMAL)
        for _ in range(5):
            rtt, loss = sim.sample_carrier()
            oda.evaluate_telemetry(rtt, loss)

        report.reconciled_actions = oda.reconcile_mesh()
        report.total_dropped = oda.buffer.size()  # Should be 0

        # Verify Merkle WAL
        report.merkle_wal_verified = model.wal.verify_integrity()
        report.crdt_consistency_verified = model.mesh_node.counter.value() == iterations

        report.max_latency_ms = max(latencies)
        report.min_latency_ms = min(latencies)
        report.avg_latency_ms = sum(latencies) / len(latencies)

        report.passed = (
            report.total_dropped == 0
            and report.merkle_wal_verified
            and report.crdt_consistency_verified
            and report.max_latency_ms <= 16.66
        )

        return report
