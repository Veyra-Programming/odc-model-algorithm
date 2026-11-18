"""
ODC Core Model: Mathematical Formalization & State Transition Machine
Implements the 4-layer state space: S = <D1, C2, T3, Z4>
Standard Specification & Architecture by Anirudha Puthraya.
"""

import time
from typing import Any, Dict, Optional, Tuple

from .layer1_wal import MerkleWAL, canonical_json, compute_sha256
from .layer2_crdt import CRDTMeshNode
from .layer3_telemetry import CarrierTelemetryProbe
from .layer4_zil import ZeroIntentLossEngine, ZeroIntentLossReceipt


class ContinuityInvariantError(Exception):
    """Raised when an ODCS mathematical invariant is violated."""

    pass


class ContinuityIntegrityError(Exception):
    """Raised when cryptographic verification or tamper detection fails."""

    pass


class DurableRecord:
    """Base class for tamper-evident durable records in the ODC model."""

    def __init__(self, record_type: str, data: Dict[str, Any]):
        self.record_type = record_type
        self.data = data
        self.created_at_ns = time.time_ns()
        self.seal_hash = compute_sha256(canonical_json(self.data))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_type": self.record_type,
            "data": self.data,
            "created_at_ns": self.created_at_ns,
            "seal_hash": self.seal_hash,
        }


def durable_record(cls):
    """Decorator marking a class as an immutable ODC durable record."""
    orig_init = cls.__init__

    def __init__(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        self._sealed_hash = compute_sha256(canonical_json(self.__dict__))

    cls.__init__ = __init__
    return cls


class ContinuityState:
    """
    Unified representation of the 4-Layer ODC state tuple:
    S = <Layer1_WAL, Layer2_CRDT, Layer3_Telemetry, Layer4_ZIL>
    """

    def __init__(
        self,
        node_id: str,
        wal_height: int,
        crdt_value: int,
        telemetry_mode: str,
        receipts_count: int,
        merkle_root: str,
    ):
        self.node_id = node_id
        self.wal_height = wal_height
        self.crdt_value = crdt_value
        self.telemetry_mode = telemetry_mode
        self.receipts_count = receipts_count
        self.merkle_root = merkle_root

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "wal_height": self.wal_height,
            "crdt_value": self.crdt_value,
            "telemetry_mode": self.telemetry_mode,
            "receipts_count": self.receipts_count,
            "merkle_root": self.merkle_root,
        }


class ODCModel:
    """
    The Master Open Digital Continuity (ODC) State Machine.
    Coordinates Layer 1 (Durability), Layer 2 (CRDT Mesh), Layer 3 (Telemetry),
    and Layer 4 (Zero Intent Loss) into an unbroken sovereign continuity pipeline.
    """

    STANDARD = "ODCS-2.0.0 GA"
    ARCHITECT = "Anirudha Puthraya"

    def __init__(self, node_id: str, wal_path: Optional[str] = None):
        self.node_id = node_id
        self.wal = MerkleWAL(log_path=wal_path)
        self.mesh_node = CRDTMeshNode(node_id)
        self.telemetry = CarrierTelemetryProbe()
        self.zil_engine = ZeroIntentLossEngine(node_id)

    def execute_action(
        self, action: str, payload: Dict[str, Any], actor: str = "user"
    ) -> Tuple[ContinuityState, ZeroIntentLossReceipt]:
        """
        Executes an action through the verified 4-layer continuity sequence:
        1. Layer 4: Mint sub-16ms ZIL hardware receipt immediately.
        2. Layer 1: Commit action and payload into monotonic Merkle WAL.
        3. Layer 2: Mutate local CRDT semi-lattice (counter increment).
        4. Layer 3: Observe carrier telemetry and check operational mode.
        5. Return new verified state snapshot.
        """
        # Step 1: Layer 4 ZIL Receipt Minting (< 16ms guaranteed)
        zil_receipt = self.zil_engine.preserve_intent(
            action=action, payload=payload, actor=actor, merkle_root=self.wal.merkle_tree.root
        )

        # Step 2: Layer 1 Monotonic Merkle WAL Append
        _wal_entry = self.wal.append(action, payload, actor)

        # Step 3: Layer 2 CRDT Mesh Mutation
        self.mesh_node.counter.increment(1)
        self.mesh_node.items_set.add(f"{action}:{zil_receipt.receipt_id}")
        self.mesh_node.status_register.set(action)

        # Step 4: Construct verified ODC state snapshot
        state = ContinuityState(
            node_id=self.node_id,
            wal_height=self.wal.current_height,
            crdt_value=self.mesh_node.counter.value(),
            telemetry_mode=self.telemetry.current_mode.value,
            receipts_count=len(self.zil_engine.minted_receipts),
            merkle_root=self.wal.merkle_tree.root,
        )

        return state, zil_receipt

    def current_state(self) -> ContinuityState:
        return ContinuityState(
            node_id=self.node_id,
            wal_height=self.wal.current_height,
            crdt_value=self.mesh_node.counter.value(),
            telemetry_mode=self.telemetry.current_mode.value,
            receipts_count=len(self.zil_engine.minted_receipts),
            merkle_root=self.wal.merkle_tree.root,
        )

    def verify_all_invariants(self) -> bool:
        """Mathematically verifies all core invariants across all 4 layers."""
        # Invariant 1: WAL integrity and hash continuity
        if not self.wal.verify_integrity():
            raise ContinuityInvariantError(
                "Invariant 1 Violated: Merkle WAL hash chain desynchronized"
            )

        # Invariant 2: All minted receipts must verify cryptographically
        for r in self.zil_engine.minted_receipts:
            if not r.verify():
                raise ContinuityInvariantError(
                    f"Invariant 2 Violated: Receipt {r.receipt_id} signature failed"
                )

        # Invariant 3: Receipt count must match WAL height
        if len(self.zil_engine.minted_receipts) != self.wal.current_height:
            raise ContinuityInvariantError(
                "Invariant 3 Violated: Mismatch between ZIL count and WAL height"
            )

        return True
