"""
ODC Layer 3: Dynamic Carrier Telemetry Sensing & Jitter Telemetry
Provides active and passive carrier-wave sensing, exponential moving average jitter tracking,
and real-time operational mode classification.
Standard Specification & Architecture by Anirudha Puthraya.
"""

import time
from enum import Enum
from typing import Any, Dict, List


class TelemetryMode(str, Enum):
    OPTIMAL_ONLINE = "OPTIMAL_ONLINE"  # RTT <= 80ms, Jitter <= 15ms
    DEGRADED_JITTER = "DEGRADED_JITTER"  # 80ms < RTT < 2000ms, or jitter > 15ms
    SEVERED_OFFLINE = "SEVERED_OFFLINE"  # Carrier cut, timeout > 2000ms, or RTT = inf


class TelemetrySample:
    """Individual carrier wave telemetry observation."""

    def __init__(
        self, timestamp_ns: int, rtt_ms: float, jitter_ms: float, packet_loss: float = 0.0
    ):
        self.timestamp_ns = timestamp_ns
        self.rtt_ms = rtt_ms
        self.jitter_ms = jitter_ms
        self.packet_loss = packet_loss

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_ns": self.timestamp_ns,
            "rtt_ms": self.rtt_ms,
            "jitter_ms": self.jitter_ms,
            "packet_loss": self.packet_loss,
        }


class CarrierTelemetryProbe:
    """
    Dynamic telemetry sensor monitoring network carrier stability.
    Maintains exponential moving averages (EMA) for RTT and jitter:
    EMA_RTT_t = (1 - alpha) * EMA_RTT_{t-1} + alpha * RTT_t
    EMA_Jitter_t = (1 - beta) * EMA_Jitter_{t-1} + beta * |RTT_t - RTT_{t-1}|
    """

    def __init__(self, alpha: float = 0.125, beta: float = 0.25):
        self.alpha = alpha
        self.beta = beta
        self.last_rtt: float = 0.04
        self.ema_rtt: float = 0.04
        self.ema_jitter: float = 0.01
        self.current_mode: TelemetryMode = TelemetryMode.OPTIMAL_ONLINE
        self.history: List[TelemetrySample] = []
        self._max_history: int = 1000

    def record_probe(self, rtt_ms: float, packet_loss: float = 0.0) -> TelemetryMode:
        now_ns = time.monotonic_ns()

        if rtt_ms == float("inf") or rtt_ms > 2000.0 or packet_loss >= 0.5:
            # Severed offline partition
            instant_jitter = 0.0
            self.current_mode = TelemetryMode.SEVERED_OFFLINE
            self.ema_rtt = float("inf")
        else:
            if self.ema_rtt == float("inf") or self.last_rtt == float("inf"):
                self.ema_rtt = rtt_ms
                self.last_rtt = rtt_ms
                self.ema_jitter = 0.0
                instant_jitter = 0.0
            else:
                instant_jitter = abs(rtt_ms - self.last_rtt)
                self.ema_rtt = (1 - self.alpha) * self.ema_rtt + self.alpha * rtt_ms
                self.last_rtt = rtt_ms
                self.ema_jitter = (1 - self.beta) * self.ema_jitter + self.beta * instant_jitter

            # Classify mode
            if self.ema_rtt > 80.0 or self.ema_jitter > 20.0 or packet_loss > 0.05:
                self.current_mode = TelemetryMode.DEGRADED_JITTER
            else:
                self.current_mode = TelemetryMode.OPTIMAL_ONLINE

        sample = TelemetrySample(now_ns, rtt_ms, instant_jitter, packet_loss)
        self.history.append(sample)
        if len(self.history) > self._max_history:
            self.history.pop(0)

        return self.current_mode

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self.current_mode.value,
            "ema_rtt_ms": round(self.ema_rtt, 3) if self.ema_rtt != float("inf") else "∞",
            "ema_jitter_ms": round(self.ema_jitter, 3),
            "samples_count": len(self.history),
        }
