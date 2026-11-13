from typing import Optional
from app.adapters.base import PlatformAdapter
from app.adapters.mock_adapter import MockPlatformAdapter
from app.adapters.brain_adapter import BrainPlatformAdapter
from app.adapters.manual_adapter import ManualImportAdapter
from app.core.config import settings

class AdapterManager:
    def __init__(self):
        self._mock = MockPlatformAdapter()
        self._brain = BrainPlatformAdapter()
        self._manual = ManualImportAdapter()
        self._current_mode = settings.integration_mode

    @property
    def current_mode(self) -> str:
        return self._current_mode

    def set_mode(self, mode: str):
        mode_upper = mode.upper()
        if mode_upper not in ("MOCK", "LIVE", "MANUAL"):
            raise ValueError(f"Invalid integration mode: {mode}. Must be MOCK, LIVE, or MANUAL.")
        self._current_mode = mode_upper

    def get_adapter(self) -> PlatformAdapter:
        if self._current_mode == "LIVE":
            return self._brain
        elif self._current_mode == "MANUAL":
            return self._manual
        return self._mock

adapter_manager = AdapterManager()
