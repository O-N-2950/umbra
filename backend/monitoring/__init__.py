"""
MATCHO — Monitoring Module
Leçon PEP's #4/#6/#8 : Ne JAMAIS attendre les catastrophes pour monitorer.

Composants:
  - HealthChecker     : Vérifie tous les services au boot + endpoint /health
  - CrashMonitor      : Surveillance périodique (toutes les 5 min)
  - AlertService      : Alertes email admin en cas de problème

© 2026 PEP's Swiss SA
"""

from monitoring.health_check import HealthChecker, ServiceStatus
from monitoring.crash_monitor import CrashMonitor
from monitoring.alerts import AlertService

__all__ = ["HealthChecker", "ServiceStatus", "CrashMonitor", "AlertService"]
