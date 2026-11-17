"""
ODC Layer 2: Conflict-Free Replicated Data Types (CRDT) Mesh Convergence
Implements state-based (CvRDT) semi-lattices guaranteeing strong eventual consistency
without central locks or single points of failure across network partitions.
Standard Specification & Architecture by Anirudha Puthraya.
"""

from typing import Any, Dict, Set, Tuple, Optional
import time
import uuid


class PNCounter:
    """
    Positive-Negative Counter (PN-Counter) CvRDT.
    Supports concurrent increments and decrements across arbitrary replicas.
    Merge operation computes the least upper bound (supremum) via component-wise maximum.
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.p_map: Dict[str, int] = {node_id: 0}
        self.n_map: Dict[str, int] = {node_id: 0}

    def increment(self, delta: int = 1) -> int:
        if delta < 0:
            return self.decrement(-delta)
        self.p_map[self.node_id] = self.p_map.get(self.node_id, 0) + delta
        return self.value()

    def decrement(self, delta: int = 1) -> int:
        if delta < 0:
            return self.increment(-delta)
        self.n_map[self.node_id] = self.n_map.get(self.node_id, 0) + delta
        return self.value()

    def value(self) -> int:
        return sum(self.p_map.values()) - sum(self.n_map.values())

    def merge(self, other: "PNCounter") -> "PNCounter":
        """Component-wise supremum: join(A, B) = max(A.p, B.p) - max(A.n, B.n)"""
        all_nodes = set(self.p_map.keys()) | set(other.p_map.keys()) | \
                    set(self.n_map.keys()) | set(other.n_map.keys())

        merged = PNCounter(self.node_id)
        merged.p_map = {n: max(self.p_map.get(n, 0), other.p_map.get(n, 0)) for n in all_nodes}
        merged.n_map = {n: max(self.n_map.get(n, 0), other.n_map.get(n, 0)) for n in all_nodes}
        return merged

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "PNCounter",
            "node_id": self.node_id,
            "value": self.value(),
            "p_map": self.p_map,
            "n_map": self.n_map
        }


class AddWinsORSet:
    """
    Add-Wins Observed-Removed Set (AW-OR-Set) CvRDT.
    Concurrent adds and removes are resolved such that adds win over concurrent deletes.
    Elements are tagged with unique causal UUID tags.
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        # Map of element -> Set of active causal UUID tags
        self.entries: Dict[Any, Set[str]] = {}
        # Tombstone set of observed and removed causal tags
        self.tombstones: Set[str] = set()

    def add(self, element: Any) -> str:
        tag = f"{self.node_id}:{uuid.uuid4().hex[:12]}"
        if element not in self.entries:
            self.entries[element] = set()
        self.entries[element].add(tag)
        return tag

    def remove(self, element: Any) -> None:
        if element in self.entries:
            # Move all observed tags to tombstones
            self.tombstones.update(self.entries[element])
            del self.entries[element]

    def contains(self, element: Any) -> bool:
        if element not in self.entries:
            return False
        # Active if there is at least one tag not in tombstones
        active_tags = self.entries[element] - self.tombstones
        return len(active_tags) > 0

    def elements(self) -> Set[Any]:
        return {elem for elem, tags in self.entries.items() if len(tags - self.tombstones) > 0}

    def merge(self, other: "AddWinsORSet") -> "AddWinsORSet":
        """Merges two sets: union tombstones, and union active tags filtered by tombstones."""
        merged = AddWinsORSet(self.node_id)
        merged.tombstones = self.tombstones | other.tombstones

        all_keys = set(self.entries.keys()) | set(other.entries.keys())
        for k in all_keys:
            tags = (self.entries.get(k, set()) | other.entries.get(k, set())) - merged.tombstones
            if tags:
                merged.entries[k] = tags
        return merged

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "AddWinsORSet",
            "node_id": self.node_id,
            "elements": sorted(list(self.elements()), key=str),
            "tombstones_count": len(self.tombstones)
        }


class LWWRegister:
    """
    Last-Write-Wins Register (LWW-Register) CvRDT.
    Concurrent values are ordered by monotonic timestamps with deterministic node tie-breaking.
    """
    def __init__(self, node_id: str, initial_value: Any = None):
        self.node_id = node_id
        self.value = initial_value
        self.timestamp = time.time_ns()

    def set(self, value: Any) -> None:
        self.value = value
        self.timestamp = time.time_ns()

    def merge(self, other: "LWWRegister") -> "LWWRegister":
        merged = LWWRegister(self.node_id)
        if other.timestamp > self.timestamp:
            merged.value = other.value
            merged.timestamp = other.timestamp
        elif other.timestamp == self.timestamp:
            # Deterministic tie-breaker
            if other.node_id > self.node_id:
                merged.value = other.value
                merged.timestamp = other.timestamp
            else:
                merged.value = self.value
                merged.timestamp = self.timestamp
        else:
            merged.value = self.value
            merged.timestamp = self.timestamp
        return merged


class CRDTMeshNode:
    """
    Autonomous node in a distributed disruption-tolerant CRDT mesh.
    Manages local CRDT state and synchronizes algebraically with peers.
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.counter = PNCounter(node_id)
        self.items_set = AddWinsORSet(node_id)
        self.status_register = LWWRegister(node_id, "INITIALIZED")

    def sync_with_peer(self, peer: "CRDTMeshNode") -> None:
        """Algebraic join semi-lattice synchronization with a peer node."""
        self.counter = self.counter.merge(peer.counter)
        peer.counter = peer.counter.merge(self.counter)

        self.items_set = self.items_set.merge(peer.items_set)
        peer.items_set = peer.items_set.merge(self.items_set)

        self.status_register = self.status_register.merge(peer.status_register)
        peer.status_register = peer.status_register.merge(self.status_register)
