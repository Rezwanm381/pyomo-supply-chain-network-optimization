"""Deterministic scenario derivation and hand-solvable fixtures."""

from __future__ import annotations

from math import hypot

import pandas as pd

from .data_loader import NetworkData, validate_network_data


def derive_transport_costs(
    facilities: pd.DataFrame,
    customers: pd.DataFrame,
    *,
    distance_rate_usd_per_unit_sdu: float,
    cost_decimals: int = 2,
) -> pd.DataFrame:
    """Derive the complete arc matrix without randomness or seed search."""

    rows: list[dict[str, object]] = []
    for facility in facilities.itertuples(index=False):
        for customer in customers.itertuples(index=False):
            distance = hypot(
                float(facility.x_coord_sdu) - float(customer.x_coord_sdu),
                float(facility.y_coord_sdu) - float(customer.y_coord_sdu),
            )
            rows.append(
                {
                    "facility_id": facility.facility_id,
                    "customer_id": customer.customer_id,
                    "distance_sdu": round(distance, 4),
                    "unit_cost_usd_per_unit": round(
                        distance_rate_usd_per_unit_sdu * distance,
                        cost_decimals,
                    ),
                    "provenance": "DERIVED_SCENARIO_VALUE",
                }
            )
    return pd.DataFrame(rows)


def make_tiny_known_case() -> NetworkData:
    """Return the 2×2 regression fixture whose manual optimum is 280."""

    facilities = pd.DataFrame(
        [
            {
                "facility_id": "A",
                "facility_name": "Fixture A",
                "x_coord_sdu": 0.0,
                "y_coord_sdu": 0.0,
                "capacity_units_per_year": 80.0,
                "fixed_cost_usd_per_year": 100.0,
                "provenance": "SYNTHETIC_TEST_VALUE",
            },
            {
                "facility_id": "B",
                "facility_name": "Fixture B",
                "x_coord_sdu": 1.0,
                "y_coord_sdu": 0.0,
                "capacity_units_per_year": 80.0,
                "fixed_cost_usd_per_year": 60.0,
                "provenance": "SYNTHETIC_TEST_VALUE",
            },
        ]
    )
    customers = pd.DataFrame(
        [
            {
                "customer_id": "C1",
                "customer_name": "Fixture Customer 1",
                "x_coord_sdu": 0.0,
                "y_coord_sdu": 1.0,
                "demand_units_per_year": 40.0,
                "provenance": "SYNTHETIC_TEST_VALUE",
            },
            {
                "customer_id": "C2",
                "customer_name": "Fixture Customer 2",
                "x_coord_sdu": 1.0,
                "y_coord_sdu": 1.0,
                "demand_units_per_year": 40.0,
                "provenance": "SYNTHETIC_TEST_VALUE",
            },
        ]
    )
    costs = {("A", "C1"): 1.0, ("A", "C2"): 8.0, ("B", "C1"): 6.0, ("B", "C2"): 2.0}
    transport = pd.DataFrame(
        [
            {
                "facility_id": facility_id,
                "customer_id": customer_id,
                "distance_sdu": 0.0,
                "unit_cost_usd_per_unit": unit_cost,
                "provenance": "SYNTHETIC_TEST_VALUE",
            }
            for (facility_id, customer_id), unit_cost in costs.items()
        ]
    )
    data = NetworkData(
        facilities=facilities,
        customers=customers,
        transport_costs=transport,
        metadata={
            "scenario_name": "TINY_KNOWN_CASE",
            "data_strategy": "MANUALLY_DERIVED_TEST_FIXTURE",
            "random_seed": "NOT_APPLICABLE",
        },
    )
    validate_network_data(data, require_capacity=True)
    return data

