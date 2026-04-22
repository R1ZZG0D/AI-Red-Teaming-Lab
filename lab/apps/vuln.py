from __future__ import annotations

from lab.apps.common import create_lab_app
from lab.shared.config import Settings
from lab.vulnerable.service import VulnerableLabService


settings = Settings.from_mode("vulnerable", "AI Red Teaming Lab - Vulnerable")
service = VulnerableLabService(settings)
app = create_lab_app(settings, "/vuln", service)

