from __future__ import annotations

from lab.apps.common import create_lab_app
from lab.secure.service import SecureLabService
from lab.shared.config import Settings


settings = Settings.from_mode("secure", "AI Red Teaming Lab - Secure")
service = SecureLabService(settings)
app = create_lab_app(settings, "/secure", service)

