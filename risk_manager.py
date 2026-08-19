"""Canonical risk-manager facade for TAFA X.

The implementation lives in risk.risk_manager; this module exists only as
a package-local import surface and contains no duplicate logic.
"""
from risk.risk_manager import RiskManager, risk_manager

__all__ = ["RiskManager", "risk_manager"]
