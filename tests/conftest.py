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


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "live_neo4j: requires live local Neo4j")
    config.addinivalue_line("markers", "live_ollama: requires live Ollama model")


@pytest.fixture(autouse=True)
def disable_neo4j(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.getenv("GRAPHEVAL_LIVE_NEO4J", "").strip().lower() in {"1", "true", "yes"}:
        return
    monkeypatch.setenv("NEO4J_ENABLED", "false")
    import src.config as config

    monkeypatch.setattr(config, "NEO4J_ENABLED", False)
