"""
Open Digital Adaptation (ODA) Algorithm Engine
Standard Specification & Architecture by Anirudha Puthraya.
"""

from .algorithm import (
    ODAAlgorithm,
    AdaptationPolicy,
    OperationalState,
    DisruptionBuffer
)
from .controller import (
    ODANetworkSimulator,
    CarrierEnvironment
)
from .verifier import (
    ODAMathematicalVerifier,
    VerificationReport
)

__version__ = "2.0.0"
__author__ = "Anirudha Puthraya"
__standard__ = "ODCS-2.0.0 GA"

__all__ = [
    "ODAAlgorithm",
    "AdaptationPolicy",
    "OperationalState",
    "DisruptionBuffer",
    "ODANetworkSimulator",
    "CarrierEnvironment",
    "ODAMathematicalVerifier",
    "VerificationReport"
]
