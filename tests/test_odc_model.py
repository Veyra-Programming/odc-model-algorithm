"""
Unit and Integration Tests for the Open Digital Continuity (ODC) Model.
Tests all 4 layers, Merkle WAL, CRDT join semi-lattices, and ZIL latency guarantees.
Standard Specification & Architecture by Anirudha Puthraya.
"""

import os
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from odc.core import ODCModel
from odc.layer1_wal import MerkleTree, MerkleWAL, canonical_json
from odc.layer2_crdt import AddWinsORSet, PNCounter
from odc.layer4_zil import ZeroIntentLossEngine


class TestLayer1MerkleWAL(unittest.TestCase):
    def test_canonical_json_sorting(self):
        # Order should be independent of dict key definition order
        d1 = {"b": 2, "a": 1, "z": {"nested": "value", "apple": 99}}
        d2 = {"z": {"apple": 99, "nested": "value"}, "a": 1, "b": 2}
        self.assertEqual(canonical_json(d1), canonical_json(d2))

    def test_merkle_tree_proof_verification(self):
        tree = MerkleTree()
        items = [{"id": i, "val": f"item_{i}"} for i in range(10)]
        for it in items:
            tree.add_leaf(it)

        # Generate and verify proof for every item
        for idx in range(len(items)):
            proof = tree.generate_proof(idx)
            self.assertTrue(proof.verify())

    def test_wal_append_and_integrity(self):
        temp_dir = tempfile.mkdtemp()
        wal_path = os.path.join(temp_dir, "test.wal")
        try:
            wal = MerkleWAL(log_path=wal_path)
            for i in range(20):
                wal.append(f"ACTION_{i}", {"index": i, "msg": "hello"})

            self.assertEqual(wal.current_height, 20)
            self.assertTrue(wal.verify_integrity())

            # Replay on fresh instance
            wal2 = MerkleWAL(log_path=wal_path)
            self.assertEqual(wal2.current_height, 20)
            self.assertEqual(wal2.merkle_tree.root, wal.merkle_tree.root)
            self.assertTrue(wal2.verify_integrity())
        finally:
            shutil.rmtree(temp_dir)


class TestLayer2CRDT(unittest.TestCase):
    def test_pn_counter_commutativity(self):
        a = PNCounter("node-a")
        b = PNCounter("node-b")

        a.increment(10)
        a.decrement(3)
        b.increment(15)
        b.decrement(7)

        # Merge commutativity: join(A, B) == join(B, A)
        m1 = a.merge(b)
        m2 = b.merge(a)
        self.assertEqual(m1.value(), m2.value())
        self.assertEqual(m1.value(), (10 - 3) + (15 - 7))

    def test_add_wins_or_set_add_wins_over_remove(self):
        s1 = AddWinsORSet("node-1")
        s2 = AddWinsORSet("node-2")

        # Node 1 adds "Apple"
        s1.add("Apple")

        # Synchronize
        s2 = s2.merge(s1)
        self.assertTrue(s2.contains("Apple"))

        # Node 1 removes "Apple" concurrently while Node 2 re-adds "Apple"
        s1.remove("Apple")
        s2.add("Apple")

        # Merge should result in "Apple" still present (Add Wins)
        merged = s1.merge(s2)
        self.assertTrue(merged.contains("Apple"))


class TestLayer4ZIL(unittest.TestCase):
    def test_sub_16ms_latency_guarantee(self):
        engine = ZeroIntentLossEngine("node-bench")
        durations = []
        for i in range(100):
            t0 = time.monotonic_ns()
            receipt = engine.preserve_intent("MINT_VITAL", {"pt": f"P-{i}", "bpm": 70 + (i % 20)})
            t1 = time.monotonic_ns()
            dur = (t1 - t0) / 1_000_000.0
            durations.append(dur)
            self.assertTrue(receipt.verify())
            self.assertLess(dur, 16.66)

        avg_dur = sum(durations) / len(durations)
        # Typically < 0.15ms on modern hardware
        self.assertLess(avg_dur, 2.0)


class TestUnifiedODCModel(unittest.TestCase):
    def test_full_model_execution_and_invariants(self):
        model = ODCModel("test-node-master")
        for i in range(50):
            state, receipt = model.execute_action(f"COMMAND_{i}", {"seq": i, "val": i * 10})
            self.assertEqual(state.wal_height, i + 1)
            self.assertEqual(state.crdt_value, i + 1)
            self.assertTrue(receipt.verify())

        self.assertTrue(model.verify_all_invariants())


if __name__ == "__main__":
    unittest.main()
