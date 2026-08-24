"""Load and validate transparent network scenario inputs."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import hypot, isfinite
from pathlib import Path
from typing import Any

import pandas as pd


class DataValidationError(ValueError):
    """Raised when an input table or scenario violates the data contract."""


class ScenarioInfeasibleError(DataValidationError):
    """Raised when aggregate potential capacity cannot cover demand."""


FACILITY_COLUMNS = {
    "facility_id",
    "facility_name",
    "x_coord_sdu",
    "y_coord_sdu",
    "capacity_units_per_year",
    "fixed_cost_usd_per_year",
    "provenance",
}
CUSTOMER_COLUMNS = {
    "customer_id",
    "customer_name",
    "x_coord_sdu",
    "y_coord_sdu",
    "demand_units_per_year",
    "provenance",
}
TRANSPORT_COLUMNS = {
    "facility_id",
    "customer_id",
    "distance_sdu",
    "unit_cost_usd_per_unit",
    "provenance",
}
SCENARIO_COLUMNS = {
    "scenario_id",
    "demand_multiplier",
    "capacity_multiplier",
    "fixed_cost_multiplier",
    "transport_cost_multiplier",
    "expected_feasible",
    "include_in_sensitivity",
    "provenance",
    "description",
}
ALLOWED_PROVENANCE = {"SCENARIO_ASSUMPTION", "DERIVED_SCENARIO_VALUE", "SYNTHETIC_TEST_VALUE"}
REQUIRED_METADATA_KEYS = {
    "scenario_name",
    "data_strategy",
    "random_seed",
    "planning_horizon",
    "distance_method",
    "distance_rate_usd_per_unit_sdu",
    "transport_cost_rounding_decimals",
}


@dataclass
class NetworkData:
    facilities: pd.DataFrame
    customers: pd.DataFrame
    transport_costs: pd.DataFrame
    metadata: dict[str, str]

    @property
    def facility_ids(self) -> list[str]:
        return self.facilities["facility_id"].tolist()

    @property
    def customer_ids(self) -> list[str]:
        return self.customers["customer_id"].tolist()

    @property
    def total_demand(self) -> float:
        return float(self.customers["demand_units_per_year"].sum())

    @property
    def total_capacity(self) -> float:
        return float(self.facilities["capacity_units_per_year"].sum())

    def copy(self) -> "NetworkData":
        return NetworkData(
            facilities=self.facilities.copy(deep=True),
            customers=self.customers.copy(deep=True),
            transport_costs=self.transport_costs.copy(deep=True),
            metadata=dict(self.metadata),
        )


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    demand_multiplier: float = 1.0
    capacity_multiplier: float = 1.0
    fixed_cost_multiplier: float = 1.0
    transport_cost_multiplier: float = 1.0
    expected_feasible: bool = True
    include_in_sensitivity: bool = True
    provenance: str = "SCENARIO_ASSUMPTION"
    description: str = ""


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise DataValidationError(f"Required input file is missing: {path}")
    try:
        return pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - pandas supplies detailed context
        raise DataValidationError(f"Could not read CSV input {path}: {exc}") from exc


def _require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise DataValidationError(f"{label} is missing required columns: {', '.join(missing)}")


def _validate_ids(frame: pd.DataFrame, column: str, label: str) -> None:
    values = frame[column].astype(str).str.strip()
    if values.eq("").any() or frame[column].isna().any():
        raise DataValidationError(f"{label} contains a blank {column}")
    duplicated = values[values.duplicated()].unique().tolist()
    if duplicated:
        raise DataValidationError(f"{label} contains duplicate {column} values: {duplicated}")
    frame[column] = values


def _coerce_numeric(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    for column in columns:
        try:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
        except Exception as exc:
            raise DataValidationError(f"{label}.{column} must be numeric") from exc
        if not frame[column].map(lambda value: isfinite(float(value))).all():
            raise DataValidationError(f"{label}.{column} contains a non-finite value")


def _reject_negative(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    for column in columns:
        if (frame[column] < 0).any():
            raise DataValidationError(f"{label}.{column} cannot be negative")


def _validate_provenance(frame: pd.DataFrame, label: str) -> None:
    values = frame["provenance"].astype(str).str.strip()
    if frame["provenance"].isna().any() or values.eq("").any():
        raise DataValidationError(f"{label}.provenance cannot be blank")
    invalid = sorted(set(values) - ALLOWED_PROVENANCE)
    if invalid:
        raise DataValidationError(f"{label}.provenance contains unsupported labels: {invalid}")
    frame["provenance"] = values


def _load_metadata(path: Path) -> dict[str, str]:
    frame = _read_csv(path)
    _require_columns(frame, {"key", "value", "unit", "provenance", "notes"}, "scenario_metadata")
    _validate_ids(frame, "key", "scenario_metadata")
    _validate_provenance(frame, "scenario_metadata")
    for column in ["value", "unit"]:
        values = frame[column].astype(str).str.strip()
        if frame[column].isna().any() or values.eq("").any():
            raise DataValidationError(f"scenario_metadata.{column} cannot be blank")
    metadata = {str(row.key): str(row.value) for row in frame.itertuples(index=False)}
    missing = sorted(REQUIRED_METADATA_KEYS - set(metadata))
    if missing:
        raise DataValidationError(f"scenario_metadata is missing required keys: {', '.join(missing)}")
    try:
        numeric_metadata = {
            "planning_horizon": float(metadata["planning_horizon"]),
            "distance_rate_usd_per_unit_sdu": float(metadata["distance_rate_usd_per_unit_sdu"]),
            "transport_cost_rounding_decimals": float(metadata["transport_cost_rounding_decimals"]),
        }
    except ValueError as exc:
        raise DataValidationError("scenario_metadata numeric values must be numeric") from exc
    if not all(isfinite(value) for value in numeric_metadata.values()):
        raise DataValidationError("scenario_metadata numeric values must be finite")
    if numeric_metadata["planning_horizon"] <= 0:
        raise DataValidationError("scenario_metadata.planning_horizon must be greater than zero")
    if numeric_metadata["distance_rate_usd_per_unit_sdu"] < 0:
        raise DataValidationError("scenario_metadata.distance_rate_usd_per_unit_sdu cannot be negative")
    rounding = numeric_metadata["transport_cost_rounding_decimals"]
    if rounding < 0 or not rounding.is_integer():
        raise DataValidationError("scenario_metadata.transport_cost_rounding_decimals must be a nonnegative integer")
    return metadata


def load_network_data(data_dir: str | Path) -> NetworkData:
    """Load base scenario CSVs and enforce their complete data contract."""

    data_path = Path(data_dir)
    facilities = _read_csv(data_path / "facilities.csv")
    customers = _read_csv(data_path / "customers.csv")
    transport = _read_csv(data_path / "transport_costs.csv")
    metadata = _load_metadata(data_path / "scenario_metadata.csv")

    _require_columns(facilities, FACILITY_COLUMNS, "facilities")
    _require_columns(customers, CUSTOMER_COLUMNS, "customers")
    _require_columns(transport, TRANSPORT_COLUMNS, "transport_costs")

    _coerce_numeric(
        facilities,
        ["x_coord_sdu", "y_coord_sdu", "capacity_units_per_year", "fixed_cost_usd_per_year"],
        "facilities",
    )
    _coerce_numeric(
        customers,
        ["x_coord_sdu", "y_coord_sdu", "demand_units_per_year"],
        "customers",
    )
    _coerce_numeric(transport, ["distance_sdu", "unit_cost_usd_per_unit"], "transport_costs")

    data = NetworkData(facilities, customers, transport, metadata)
    validate_network_data(data, require_capacity=True, verify_transport_formula=True)
    return data


def validate_network_data(
    data: NetworkData,
    *,
    require_capacity: bool = True,
    verify_transport_formula: bool = False,
) -> None:
    """Validate identifiers, domains, arc completeness, and optional feasibility."""

    _require_columns(data.facilities, FACILITY_COLUMNS, "facilities")
    _require_columns(data.customers, CUSTOMER_COLUMNS, "customers")
    _require_columns(data.transport_costs, TRANSPORT_COLUMNS, "transport_costs")

    _validate_ids(data.facilities, "facility_id", "facilities")
    _validate_ids(data.customers, "customer_id", "customers")
    _coerce_numeric(
        data.facilities,
        ["x_coord_sdu", "y_coord_sdu", "capacity_units_per_year", "fixed_cost_usd_per_year"],
        "facilities",
    )
    _coerce_numeric(
        data.customers,
        ["x_coord_sdu", "y_coord_sdu", "demand_units_per_year"],
        "customers",
    )
    _coerce_numeric(data.transport_costs, ["distance_sdu", "unit_cost_usd_per_unit"], "transport_costs")
    _reject_negative(data.facilities, ["capacity_units_per_year", "fixed_cost_usd_per_year"], "facilities")
    _reject_negative(data.customers, ["demand_units_per_year"], "customers")
    _reject_negative(data.transport_costs, ["distance_sdu", "unit_cost_usd_per_unit"], "transport_costs")
    _validate_provenance(data.facilities, "facilities")
    _validate_provenance(data.customers, "customers")
    _validate_provenance(data.transport_costs, "transport_costs")

    if data.facilities.empty or data.customers.empty:
        raise DataValidationError("At least one facility and one customer are required")

    if data.transport_costs[["facility_id", "customer_id"]].isna().any().any():
        raise DataValidationError("transport_costs contains blank arc identifiers")
    duplicate_arcs = data.transport_costs.duplicated(["facility_id", "customer_id"], keep=False)
    if duplicate_arcs.any():
        pairs = data.transport_costs.loc[duplicate_arcs, ["facility_id", "customer_id"]].values.tolist()
        raise DataValidationError(f"transport_costs contains duplicate arcs: {pairs}")

    facility_ids = set(data.facility_ids)
    customer_ids = set(data.customer_ids)
    arc_facilities = set(data.transport_costs["facility_id"].astype(str))
    arc_customers = set(data.transport_costs["customer_id"].astype(str))
    unknown_facilities = sorted(arc_facilities - facility_ids)
    unknown_customers = sorted(arc_customers - customer_ids)
    if unknown_facilities or unknown_customers:
        raise DataValidationError(
            f"transport_costs references unknown IDs: facilities={unknown_facilities}, customers={unknown_customers}"
        )

    expected_arcs = set(product(data.facility_ids, data.customer_ids))
    actual_arcs = set(
        data.transport_costs[["facility_id", "customer_id"]].itertuples(index=False, name=None)
    )
    missing_arcs = sorted(expected_arcs - actual_arcs)
    if missing_arcs:
        raise DataValidationError(f"transport_costs is missing {len(missing_arcs)} required arcs: {missing_arcs[:5]}")

    if verify_transport_formula:
        if "distance_rate_usd_per_unit_sdu" not in data.metadata:
            raise DataValidationError("Transport-formula validation requires distance_rate_usd_per_unit_sdu metadata")
        rate = float(data.metadata["distance_rate_usd_per_unit_sdu"])
        if not isfinite(rate) or rate < 0:
            raise DataValidationError("distance_rate_usd_per_unit_sdu must be finite and nonnegative")
        decimals = int(float(data.metadata.get("transport_cost_rounding_decimals", "2")))
        facility_xy = data.facilities.set_index("facility_id")[["x_coord_sdu", "y_coord_sdu"]]
        customer_xy = data.customers.set_index("customer_id")[["x_coord_sdu", "y_coord_sdu"]]
        for row in data.transport_costs.itertuples(index=False):
            fx, fy = facility_xy.loc[row.facility_id]
            cx, cy = customer_xy.loc[row.customer_id]
            expected_distance = hypot(float(fx) - float(cx), float(fy) - float(cy))
            if abs(float(row.distance_sdu) - round(expected_distance, 4)) > 1e-4:
                raise DataValidationError(
                    f"distance_sdu does not match coordinates for {row.facility_id}->{row.customer_id}"
                )
            expected_cost = round(rate * expected_distance, decimals)
            if abs(float(row.unit_cost_usd_per_unit) - expected_cost) > 10 ** (-(decimals + 1)):
                raise DataValidationError(
                    f"unit cost does not match documented formula for {row.facility_id}->{row.customer_id}"
                )

    if require_capacity:
        assert_capacity_feasible(data)


def assert_capacity_feasible(data: NetworkData, tolerance: float = 1e-9) -> None:
    if data.total_capacity + tolerance < data.total_demand:
        raise ScenarioInfeasibleError(
            "Insufficient total capacity: "
            f"potential capacity={data.total_capacity:.6g}, demand={data.total_demand:.6g}"
        )


def _parse_bool(value: Any, field: str) -> bool:
    normalized = str(value).strip().upper()
    if normalized not in {"TRUE", "FALSE"}:
        raise DataValidationError(f"{field} must be TRUE or FALSE")
    return normalized == "TRUE"


def load_scenarios(path: str | Path) -> list[ScenarioDefinition]:
    frame = _read_csv(Path(path))
    _require_columns(frame, SCENARIO_COLUMNS, "scenarios")
    _validate_ids(frame, "scenario_id", "scenarios")
    multiplier_columns = [
        "demand_multiplier",
        "capacity_multiplier",
        "fixed_cost_multiplier",
        "transport_cost_multiplier",
    ]
    _coerce_numeric(frame, multiplier_columns, "scenarios")
    if (frame[["demand_multiplier", "capacity_multiplier"]] <= 0).any().any():
        raise DataValidationError("Demand and capacity multipliers must be greater than zero")
    if (frame[["fixed_cost_multiplier", "transport_cost_multiplier"]] < 0).any().any():
        raise DataValidationError("Cost multipliers cannot be negative")

    definitions: list[ScenarioDefinition] = []
    for row in frame.itertuples(index=False):
        provenance = str(row.provenance).strip()
        if provenance not in ALLOWED_PROVENANCE:
            raise DataValidationError(f"scenarios.provenance contains unsupported label: {provenance}")
        definitions.append(
            ScenarioDefinition(
                scenario_id=str(row.scenario_id),
                demand_multiplier=float(row.demand_multiplier),
                capacity_multiplier=float(row.capacity_multiplier),
                fixed_cost_multiplier=float(row.fixed_cost_multiplier),
                transport_cost_multiplier=float(row.transport_cost_multiplier),
                expected_feasible=_parse_bool(row.expected_feasible, "expected_feasible"),
                include_in_sensitivity=_parse_bool(row.include_in_sensitivity, "include_in_sensitivity"),
                provenance=provenance,
                description=str(row.description),
            )
        )
    return definitions


def apply_scenario(base_data: NetworkData, scenario: ScenarioDefinition) -> NetworkData:
    """Return a scaled copy; never mutate the base data object."""

    data = base_data.copy()
    data.customers["demand_units_per_year"] *= scenario.demand_multiplier
    data.facilities["capacity_units_per_year"] *= scenario.capacity_multiplier
    data.facilities["fixed_cost_usd_per_year"] *= scenario.fixed_cost_multiplier
    data.transport_costs["unit_cost_usd_per_unit"] *= scenario.transport_cost_multiplier
    data.metadata.update(
        {
            "active_scenario": scenario.scenario_id,
            "demand_multiplier": str(scenario.demand_multiplier),
            "capacity_multiplier": str(scenario.capacity_multiplier),
            "fixed_cost_multiplier": str(scenario.fixed_cost_multiplier),
            "transport_cost_multiplier": str(scenario.transport_cost_multiplier),
        }
    )
    validate_network_data(data, require_capacity=False, verify_transport_formula=False)
    return data
