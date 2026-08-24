"""Data-contract and pre-solve feasibility tests."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import (
    CUSTOMER_COLUMNS,
    FACILITY_COLUMNS,
    TRANSPORT_COLUMNS,
    DataValidationError,
    ScenarioInfeasibleError,
    assert_capacity_feasible,
    load_network_data,
    validate_network_data,
)


DEVELOPMENT_DIR = Path(__file__).resolve().parents[1]
SCENARIO_DATA_DIR = DEVELOPMENT_DIR / "data" / "scenario"


def _copy_network_inputs(destination: Path) -> None:
    destination.mkdir()
    for filename in [
        "facilities.csv",
        "customers.csv",
        "transport_costs.csv",
        "scenario_metadata.csv",
    ]:
        shutil.copy2(SCENARIO_DATA_DIR / filename, destination / filename)


def test_checked_in_data_satisfies_schema_and_complete_arc_contract(base_data):
    assert FACILITY_COLUMNS <= set(base_data.facilities.columns)
    assert CUSTOMER_COLUMNS <= set(base_data.customers.columns)
    assert TRANSPORT_COLUMNS <= set(base_data.transport_costs.columns)

    expected_arcs = {
        (facility, customer)
        for facility in base_data.facility_ids
        for customer in base_data.customer_ids
    }
    actual_arcs = set(
        base_data.transport_costs[["facility_id", "customer_id"]].itertuples(
            index=False, name=None
        )
    )
    assert (len(base_data.facility_ids), len(base_data.customer_ids)) == (6, 12)
    assert actual_arcs == expected_arcs
    assert len(actual_arcs) == 72


def test_missing_required_schema_column_is_rejected(base_data):
    invalid = base_data.copy()
    invalid.facilities = invalid.facilities.drop(columns=["capacity_units_per_year"])

    with pytest.raises(
        DataValidationError,
        match="facilities is missing required columns: capacity_units_per_year",
    ):
        validate_network_data(invalid)


@pytest.mark.parametrize(
    ("table_attribute", "id_column", "table_label"),
    [
        ("facilities", "facility_id", "facilities"),
        ("customers", "customer_id", "customers"),
    ],
)
def test_duplicate_entity_ids_are_rejected(
    base_data,
    table_attribute: str,
    id_column: str,
    table_label: str,
):
    invalid = base_data.copy()
    frame = getattr(invalid, table_attribute)
    frame.loc[frame.index[1], id_column] = frame.loc[frame.index[0], id_column]

    message = f"{table_label} contains duplicate {id_column} values"
    with pytest.raises(DataValidationError, match=re.escape(message)):
        validate_network_data(invalid)


@pytest.mark.parametrize(
    ("table_attribute", "column", "table_label"),
    [
        ("customers", "demand_units_per_year", "customers"),
        ("facilities", "capacity_units_per_year", "facilities"),
    ],
)
def test_negative_demand_or_capacity_is_rejected(
    base_data,
    table_attribute: str,
    column: str,
    table_label: str,
):
    invalid = base_data.copy()
    frame = getattr(invalid, table_attribute)
    frame.loc[frame.index[0], column] = -1.0

    message = f"{table_label}.{column} cannot be negative"
    with pytest.raises(DataValidationError, match=re.escape(message)):
        validate_network_data(invalid, require_capacity=False)


def test_insufficient_total_capacity_is_detected_before_solving(base_data):
    invalid = base_data.copy()
    invalid.facilities["capacity_units_per_year"] = 1.0

    with pytest.raises(ScenarioInfeasibleError, match="Insufficient total capacity"):
        assert_capacity_feasible(invalid)


def test_unsupported_provenance_is_rejected_for_every_network_table(base_data):
    for table_attribute in ["facilities", "customers", "transport_costs"]:
        invalid = base_data.copy()
        frame = getattr(invalid, table_attribute)
        frame.loc[frame.index[0], "provenance"] = "UNVERIFIED_SOURCE"

        with pytest.raises(
            DataValidationError,
            match=rf"{table_attribute}\.provenance contains unsupported labels",
        ):
            validate_network_data(invalid, require_capacity=False)


def test_metadata_provenance_is_enforced(tmp_path):
    input_dir = tmp_path / "invalid_metadata_provenance"
    _copy_network_inputs(input_dir)
    metadata_path = input_dir / "scenario_metadata.csv"
    metadata = pd.read_csv(metadata_path)
    metadata.loc[metadata.index[0], "provenance"] = "UNVERIFIED_SOURCE"
    metadata.to_csv(metadata_path, index=False)

    with pytest.raises(
        DataValidationError,
        match=r"scenario_metadata\.provenance contains unsupported labels",
    ):
        load_network_data(input_dir)


def test_all_required_metadata_keys_must_be_present(tmp_path):
    input_dir = tmp_path / "missing_required_metadata"
    _copy_network_inputs(input_dir)
    metadata_path = input_dir / "scenario_metadata.csv"
    metadata = pd.read_csv(metadata_path)
    metadata = metadata.loc[metadata["key"] != "scenario_name"]
    metadata.to_csv(metadata_path, index=False)

    with pytest.raises(
        DataValidationError,
        match="scenario_metadata is missing required keys: scenario_name",
    ):
        load_network_data(input_dir)


def test_nonfinite_numeric_metadata_is_rejected_by_network_loader(tmp_path):
    numeric_keys = [
        "planning_horizon",
        "distance_rate_usd_per_unit_sdu",
        "transport_cost_rounding_decimals",
    ]
    for index, key in enumerate(numeric_keys):
        input_dir = tmp_path / f"nonfinite_metadata_{index}"
        _copy_network_inputs(input_dir)
        metadata_path = input_dir / "scenario_metadata.csv"
        metadata = pd.read_csv(metadata_path)
        metadata.loc[metadata["key"] == key, "value"] = "inf"
        metadata.to_csv(metadata_path, index=False)

        with pytest.raises(
            DataValidationError,
            match="scenario_metadata numeric values must be finite",
        ):
            load_network_data(input_dir)
