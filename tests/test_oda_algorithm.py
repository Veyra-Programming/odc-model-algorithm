"""
Unit tests for the Open Digital Adaptation (ODA) Algorithm.
Tests state transitions, buffer draining, network blackout failover, and mathematical verifier.
Standard Specification & Architecture by Anirudha Puthraya.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from odc.core import ODCModel
from oda.algorithm import ODAAlgorithm, OperationalState, AdaptationPolicy
from oda.controller import ODANetworkSimulator, CarrierEnvironment
from oda.verifier import ODAMathematicalVerifier


class TestODAAlgorithm(unittest.TestCase):
    def setUp(self):
        self.model = ODCModel("node-oda-test")
        self.oda = ODAAlgorithm(self.model)

    def test_state_transitions(self):
        # 1. Start in optimal
        self.assertEqual(self.oda.current_state, OperationalState.OPTIMAL_ONLINE)

        # 2. Inject heavy jitter (480ms)
        state = self.oda.evaluate_telemetry(rtt_ms=480.0, packet_loss=0.08)
        self.assertEqual(state, OperationalState.DEGRADED_JITTER)

        # 3. Inject total blackout (carrier cut)
        state = self.oda.evaluate_telemetry(rtt_ms=float('inf'), packet_loss=1.0)
        self.assertEqual(state, OperationalState.SEVERED_OFFLINE)

        # 4. Settle back to optimal (requires 3 consecutive good probes by policy)
        for _ in range(3):
            state = self.oda.evaluate_telemetry(rtt_ms=10.0, packet_loss=0.0)
        self.assertEqual(state, OperationalState.OPTIMAL_ONLINE)

    def test_disruption_buffer_and_drain(self):
        # Cut carrier
        self.oda.evaluate_telemetry(rtt_ms=float('inf'), packet_loss=1.0)
        self.assertEqual(self.oda.current_state, OperationalState.SEVERED_OFFLINE)

        # Submit 25 operations during blackout
        for i in range(25):
            self.oda.submit_action(f"OFFLINE_OP_{i}", {"index": i})

        self.assertEqual(self.oda.buffer.size(), 25)
        self.assertEqual(self.model.wal.current_height, 25)

        # Restore carrier
        for _ in range(3):
            self.oda.evaluate_telemetry(rtt_ms=12.0, packet_loss=0.0)

        # Buffer should automatically flush upon settling back to OPTIMAL_ONLINE
        self.assertEqual(self.oda.buffer.size(), 0)
        self.assertEqual(self.oda.buffer.total_flushed, 25)

    def test_formal_mathematical_verifier(self):
        report = ODAMathematicalVerifier.verify_resilience(iterations=300)
        self.assertTrue(report.passed)
        self.assertEqual(report.total_dropped, 0)
        self.assertTrue(report.merkle_wal_verified)
        self.assertTrue(report.crdt_consistency_verified)
        self.assertLessEqual(report.max_latency_ms, 16.66)


if __name__ == "__main__":
    unittest.main()
