"""Shared pytest configuration for GraphEval tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("NEO4J_ENABLED", "false")

import pytest


@pytest.fixture(autouse=True)
def disable_neo4j(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEO4J_ENABLED", "false")
    import src.config as config

    monkeypatch.setattr(config, "NEO4J_ENABLED", False)
