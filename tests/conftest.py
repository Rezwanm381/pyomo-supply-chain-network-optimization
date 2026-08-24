"""Shared fixtures for the clean-room network optimization test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.data_loader import load_network_data
from src.model import build_model
from src.scenario import make_tiny_known_case
from src.solve import solve_model


DEVELOPMENT_DIR = Path(__file__).resolve().parents[1]
SCENARIO_DATA_DIR = DEVELOPMENT_DIR / "data" / "scenario"


@pytest.fixture()
def base_data():
    """Return a fresh copy of the checked-in deterministic scenario."""

    return load_network_data(SCENARIO_DATA_DIR)


@pytest.fixture()
def tiny_data():
    """Return the independently constructed 2 x 2 regression case."""

    return make_tiny_known_case()


@pytest.fixture()
def solved_tiny(tiny_data):
    """Build and optimally solve a fresh tiny-case model."""

    model = build_model(tiny_data)
    solve_info = solve_model(model)
    return tiny_data, model, solve_info
