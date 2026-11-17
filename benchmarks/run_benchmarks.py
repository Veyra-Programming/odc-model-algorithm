"""
ODC Model & ODA Algorithm High-Resolution Performance Benchmarks
Measures sub-16ms ZIL hardware receipt minting, Merkle root calculation throughput,
and CRDT lattice convergence rates.
Standard Specification & Architecture by Anirudha Puthraya.
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from odc.core import ODCModel
from oda.algorithm import ODAAlgorithm


def run_benchmark(iterations: int = 5000):
    print("=" * 70)
    print("⚡ ODC MODEL & ODA ALGORITHM HIGH-RESOLUTION BENCHMARK")
    print(f"   Executing {iterations} continuous operations")
    print("=" * 70)

    model = ODCModel("bench-node-01")
    oda = ODAAlgorithm(model)

    durations = []
    receipt_latencies = []
    t_start = time.monotonic_ns()

    for i in range(iterations):
        t0 = time.monotonic_ns()
        state, receipt = oda.submit_action(
            f"TELEMETRY_LOG_{i}",
            {"seq": i, "reading": 42.0 + (i % 100), "device": "SENSOR_A"},
            actor="benchmark_engine"
        )
        t1 = time.monotonic_ns()
        durations.append((t1 - t0) / 1_000_000.0)
        receipt_latencies.append(receipt.duration_ms)

    t_end = time.monotonic_ns()
    total_time_sec = (t_end - t_start) / 1_000_000_000.0

    durations.sort()
    receipt_latencies.sort()

    min_lat = durations[0]
    p50_lat = durations[len(durations) // 2]
    p95_lat = durations[int(len(durations) * 0.95)]
    p99_lat = durations[int(len(durations) * 0.99)]
    max_lat = durations[-1]
    avg_lat = sum(durations) / len(durations)
    ops_per_sec = iterations / total_time_sec

    zil_p50 = receipt_latencies[len(receipt_latencies) // 2]
    zil_p99 = receipt_latencies[int(len(receipt_latencies) * 0.99)]
    zil_max = receipt_latencies[-1]

    print(f"\nEnd-to-End Operation Benchmark ({iterations} ops):")
    print(f"  • Total Execution Time : {total_time_sec:.3f} s")
    print(f"  • Throughput           : {ops_per_sec:,.0f} ops/sec")
    print(f"  • Min Latency          : {min_lat:.3f} ms")
    print(f"  • p50 (Median) Latency : {p50_lat:.3f} ms")
    print(f"  • p95 Latency          : {p95_lat:.3f} ms")
    print(f"  • p99 Latency          : {p99_lat:.3f} ms")
    print(f"  • Max Latency          : {max_lat:.3f} ms")
    print(f"  • Average Latency      : {avg_lat:.3f} ms")

    print(f"\nLayer 4 Zero Intent Loss (ZIL) Minting Guarantees:")
    print(f"  • ZIL p50 Latency      : {zil_p50:.4f} ms")
    print(f"  • ZIL p99 Latency      : {zil_p99:.4f} ms")
    print(f"  • ZIL Max Latency      : {zil_max:.4f} ms (Target: <= 16.66ms)")

    assert zil_max <= 16.66, f"ZIL violation: max ZIL latency {zil_max}ms exceeded 16.66ms"
    assert p99_lat <= 16.66, f"SLA violation: p99 latency {p99_lat}ms exceeded 16.66ms single-frame budget"
    print("\n✓ PASSED: Strict sub-16.6ms Zero Intent Loss guarantee verified!")


if __name__ == "__main__":
    run_benchmark(5000)
