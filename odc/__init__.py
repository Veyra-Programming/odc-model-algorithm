"""
Open Digital Continuity Standard (ODCS) - Core Model & Invariant Engine
Standard Specification & Architecture by Anirudha Puthraya.
"""

from .core import (
    ODCModel,
    ContinuityState,
    ContinuityInvariantError,
    ContinuityIntegrityError,
    DurableRecord,
    durable_record
)
from .layer1_wal import (
    MerkleWAL,
    MerkleTree,
    MerkleProof,
    canonical_json,
    compute_sha256
)
from .layer2_crdt import (
    PNCounter,
    AddWinsORSet,
    LWWRegister,
    CRDTMeshNode
)
from .layer3_telemetry import (
    CarrierTelemetryProbe,
    TelemetrySample,
    TelemetryMode
)
from .layer4_zil import (
    ZeroIntentLossReceipt,
    ZeroIntentLossEngine
)

__version__ = "2.0.0"
__author__ = "Anirudha Puthraya"
__standard__ = "ODCS-2.0.0 GA"

__all__ = [
    "ODCModel",
    "ContinuityState",
    "ContinuityInvariantError",
    "ContinuityIntegrityError",
    "DurableRecord",
    "durable_record",
    "MerkleWAL",
    "MerkleTree",
    "MerkleProof",
    "canonical_json",
    "compute_sha256",
    "PNCounter",
    "AddWinsORSet",
    "LWWRegister",
    "CRDTMeshNode",
    "CarrierTelemetryProbe",
    "TelemetrySample",
    "TelemetryMode",
    "ZeroIntentLossReceipt",
    "ZeroIntentLossEngine"
]
