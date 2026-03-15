"""pytest共通設定."""

import pytest


def pytest_configure(config):
    """カスタムマーカーを登録."""
    config.addinivalue_line(
        "markers",
        "gpu: mark test as requiring GPU (skip with -m 'not gpu')",
    )
