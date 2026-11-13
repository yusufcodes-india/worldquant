import pytest
from app.adapters.manager import adapter_manager

@pytest.fixture(autouse=True)
def ensure_mock_adapter_for_tests():
    adapter_manager.set_mode("MOCK")
    yield
