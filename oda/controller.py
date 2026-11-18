"""
ODA Network Controller & Chaos Simulator
Simulates real-world network phenomena: satellite jitter, carrier blackout, packet loss, and flapping.
Standard Specification & Architecture by Anirudha Puthraya.
"""

import random
from enum import Enum
from typing import Tuple


class CarrierEnvironment(str, Enum):
    FIBER_OPTIMAL = "FIBER_OPTIMAL"  # RTT ~ 5ms, Jitter ~ 1ms
    CELLULAR_4G_5G = "CELLULAR_4G_5G"  # RTT ~ 45ms, Jitter ~ 10ms
    STARLINK_SATELLITE = "STARLINK"  # RTT ~ 120ms, Jitter ~ 40ms
    UNDERGROUND_SUBWAY = "SUBWAY"  # Intermittent bursts & timeouts
    TOTAL_BLACKOUT = "TOTAL_BLACKOUT"  # Severed carrier, RTT = inf


class ODANetworkSimulator:
    """
    Chaos simulator injecting network disruption profiles into the ODA algorithm.
    Used for automated resilience testing and mathematical verification.
    """

    def __init__(self, default_env: CarrierEnvironment = CarrierEnvironment.FIBER_OPTIMAL):
        self.environment = default_env

    def set_environment(self, env: CarrierEnvironment) -> None:
        self.environment = env

    def sample_carrier(self) -> Tuple[float, float]:
        """Returns (rtt_ms, packet_loss) for current environment."""
        if self.environment == CarrierEnvironment.FIBER_OPTIMAL:
            return (random.uniform(2.0, 15.0), 0.0)
        elif self.environment == CarrierEnvironment.CELLULAR_4G_5G:
            return (random.uniform(35.0, 75.0), random.uniform(0.0, 0.02))
        elif self.environment == CarrierEnvironment.STARLINK_SATELLITE:
            return (random.uniform(90.0, 480.0), random.uniform(0.01, 0.08))
        elif self.environment == CarrierEnvironment.UNDERGROUND_SUBWAY:
            if random.random() < 0.6:
                return (float("inf"), 1.0)
            return (random.uniform(200.0, 1200.0), 0.15)
        elif self.environment == CarrierEnvironment.TOTAL_BLACKOUT:
            return (float("inf"), 1.0)
        return (20.0, 0.0)
