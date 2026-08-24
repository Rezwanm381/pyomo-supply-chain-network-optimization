"""Independent post-solve extraction and mathematical validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isclose
from typing import Any

import pandas as pd
from pyomo.environ import ConcreteModel, value

from .data_loader import NetworkData
from .solve import SolveInfo


FEASIBILITY_TOLERANCE = 1e-6
BINARY_TOLERANCE = 1e-6
OBJECTIVE_ABSOLUTE_TOLERANCE = 1e-5
OBJECTIVE_RELATIVE_TOLERANCE = 1e-6


class SolutionValidationError(RuntimeError):
    """Raised when an independently checked solution violates a quality gate."""


@dataclass
class SolutionTables:
    facilities: pd.DataFrame
    shipments: pd.DataFrame
    customers: pd.DataFrame
    cost_breakdown: pd.DataFrame
    kpis: dict[str, float | int]


@dataclass
class ValidationReport:
    passed: bool
    violations: list[str]
    max_demand_absolute_difference: float
    max_capacity_excess: float
    max_closed_facility_flow: float
    minimum_shipment: float
    max_binary_domain_distance: float
    fixed_cost_recomputed: float
    transport_cost_recomputed: float
    objective_recomputed: float
    solver_objective: float
    objective_absolute_difference: float
    feasibility_tolerance: float = FEASIBILITY_TOLERANCE
    binary_tolerance: float = BINARY_TOLERANCE
    objective_absolute_tolerance: float = OBJECTIVE_ABSOLUTE_TOLERANCE
    objective_relative_tolerance: float = OBJECTIVE_RELATIVE_TOLERANCE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_solution(
    model: ConcreteModel,
    data: NetworkData,
    solve_info: SolveInfo,
    *,
    flow_tolerance: float = FEASIBILITY_TOLERANCE,
) -> SolutionTables:
    """Create decision tables without hard-coding any final values."""

    facility_input = data.facilities.set_index("facility_id")
    customer_input = data.customers.set_index("customer_id")
    transport_input = data.transport_costs.set_index(["facility_id", "customer_id"])

    facility_rows: list[dict[str, Any]] = []
    selected_capacity = 0.0
    open_utilizations: list[float] = []
    for facility in data.facility_ids:
        raw_open = float(value(model.open_facility[facility]))
        is_open = int(raw_open >= 0.5)
        assigned = sum(float(value(model.shipment[facility, customer])) for customer in data.customer_ids)
        capacity = float(facility_input.loc[facility, "capacity_units_per_year"])
        fixed_cost = float(facility_input.loc[facility, "fixed_cost_usd_per_year"])
        utilization = assigned / capacity if is_open and capacity > 0 else 0.0
        if is_open:
            selected_capacity += capacity
            open_utilizations.append(utilization)
        facility_rows.append(
            {
                "facility_id": facility,
                "facility_name": facility_input.loc[facility, "facility_name"],
                "open": is_open,
                "open_value_raw": raw_open,
                "capacity_units_per_year": capacity,
                "assigned_flow_units_per_year": assigned,
                "utilization": utilization,
                "unused_capacity_units_per_year": capacity - assigned if is_open else 0.0,
                "fixed_cost_usd_per_year": fixed_cost,
                "fixed_cost_contribution_usd_per_year": fixed_cost * is_open,
                "capacity_binding": bool(is_open and abs(assigned - capacity) <= flow_tolerance),
            }
        )

    shipment_rows: list[dict[str, Any]] = []
    for facility in data.facility_ids:
        for customer in data.customer_ids:
            shipment = float(value(model.shipment[facility, customer]))
            if shipment <= flow_tolerance:
                continue
            unit_cost = float(transport_input.loc[(facility, customer), "unit_cost_usd_per_unit"])
            shipment_rows.append(
                {
                    "origin": facility,
                    "origin_name": facility_input.loc[facility, "facility_name"],
                    "destination": customer,
                    "destination_name": customer_input.loc[customer, "customer_name"],
                    "shipment_units_per_year": shipment,
                    "distance_sdu": float(transport_input.loc[(facility, customer), "distance_sdu"]),
                    "unit_cost_usd_per_unit": unit_cost,
                    "transport_cost_usd_per_year": shipment * unit_cost,
                }
            )

    customer_rows: list[dict[str, Any]] = []
    for customer in data.customer_ids:
        demand = float(customer_input.loc[customer, "demand_units_per_year"])
        delivered = sum(float(value(model.shipment[facility, customer])) for facility in data.facility_ids)
        customer_rows.append(
            {
                "customer_id": customer,
                "customer_name": customer_input.loc[customer, "customer_name"],
                "demand_units_per_year": demand,
                "delivered_units_per_year": delivered,
                "difference_units_per_year": delivered - demand,
            }
        )

    fixed_cost = float(value(model.fixed_cost_component))
    transport_cost = float(value(model.transport_cost_component))
    total_cost = fixed_cost + transport_cost
    facilities_frame = pd.DataFrame(facility_rows)
    shipments_frame = pd.DataFrame(
        shipment_rows,
        columns=[
            "origin",
            "origin_name",
            "destination",
            "destination_name",
            "shipment_units_per_year",
            "distance_sdu",
            "unit_cost_usd_per_unit",
            "transport_cost_usd_per_year",
        ],
    )
    customers_frame = pd.DataFrame(customer_rows)
    cost_frame = pd.DataFrame(
        [
            {"cost_component": "TOTAL_FIXED_COST", "scenario_cost_usd_per_year": fixed_cost},
            {"cost_component": "TOTAL_TRANSPORT_COST", "scenario_cost_usd_per_year": transport_cost},
            {"cost_component": "TOTAL_OBJECTIVE_COST", "scenario_cost_usd_per_year": total_cost},
        ]
    )
    total_demand = float(customers_frame["demand_units_per_year"].sum())
    kpis: dict[str, float | int] = {
        "total_scenario_cost_usd_per_year": total_cost,
        "fixed_cost_usd_per_year": fixed_cost,
        "transport_cost_usd_per_year": transport_cost,
        "facilities_opened": int(facilities_frame["open"].sum()),
        "average_open_facility_utilization": float(sum(open_utilizations) / len(open_utilizations))
        if open_utilizations
        else 0.0,
        "network_utilization": total_demand / selected_capacity if selected_capacity > 0 else 0.0,
        "maximum_open_facility_utilization": float(max(open_utilizations)) if open_utilizations else 0.0,
        "unused_selected_capacity_units_per_year": selected_capacity - total_demand,
        "demand_served_units_per_year": float(customers_frame["delivered_units_per_year"].sum()),
        "solver_objective_usd_per_year": solve_info.objective_value,
    }
    return SolutionTables(facilities_frame, shipments_frame, customers_frame, cost_frame, kpis)


def validate_solution(
    model: ConcreteModel,
    data: NetworkData,
    solve_info: SolveInfo,
) -> ValidationReport:
    """Recompute domains, constraints, and objective independently of Pyomo rows."""

    facility_input = data.facilities.set_index("facility_id")
    customer_input = data.customers.set_index("customer_id")
    cost_input = data.transport_costs.set_index(["facility_id", "customer_id"])
    open_values = {facility: float(value(model.open_facility[facility])) for facility in data.facility_ids}
    shipments = {
        (facility, customer): float(value(model.shipment[facility, customer]))
        for facility in data.facility_ids
        for customer in data.customer_ids
    }

    demand_differences = []
    for customer in data.customer_ids:
        delivered = sum(shipments[facility, customer] for facility in data.facility_ids)
        demand = float(customer_input.loc[customer, "demand_units_per_year"])
        demand_differences.append(abs(delivered - demand))

    capacity_excesses = []
    closed_flows = []
    for facility in data.facility_ids:
        assigned = sum(shipments[facility, customer] for customer in data.customer_ids)
        capacity = float(facility_input.loc[facility, "capacity_units_per_year"])
        capacity_excesses.append(max(0.0, assigned - capacity * open_values[facility]))
        if open_values[facility] < 0.5:
            closed_flows.append(assigned)

    minimum_shipment = min(shipments.values())
    binary_distances = [min(abs(open_value), abs(open_value - 1.0)) for open_value in open_values.values()]
    fixed_recomputed = sum(
        float(facility_input.loc[facility, "fixed_cost_usd_per_year"]) * open_values[facility]
        for facility in data.facility_ids
    )
    transport_recomputed = sum(
        float(cost_input.loc[(facility, customer), "unit_cost_usd_per_unit"]) * shipments[facility, customer]
        for facility in data.facility_ids
        for customer in data.customer_ids
    )
    objective_recomputed = fixed_recomputed + transport_recomputed
    objective_difference = abs(objective_recomputed - solve_info.objective_value)

    violations: list[str] = []
    max_demand_difference = max(demand_differences, default=0.0)
    max_capacity_excess = max(capacity_excesses, default=0.0)
    max_closed_flow = max(closed_flows, default=0.0)
    max_binary_distance = max(binary_distances, default=0.0)
    if max_demand_difference > FEASIBILITY_TOLERANCE:
        violations.append(f"Demand balance residual {max_demand_difference:.6g} exceeds tolerance")
    if max_capacity_excess > FEASIBILITY_TOLERANCE:
        violations.append(f"Capacity excess {max_capacity_excess:.6g} exceeds tolerance")
    if max_closed_flow > FEASIBILITY_TOLERANCE:
        violations.append(f"Closed-facility flow {max_closed_flow:.6g} exceeds tolerance")
    if minimum_shipment < -FEASIBILITY_TOLERANCE:
        violations.append(f"Negative shipment {minimum_shipment:.6g} violates nonnegativity")
    if max_binary_distance > BINARY_TOLERANCE:
        violations.append(f"Binary-domain distance {max_binary_distance:.6g} exceeds tolerance")
    if not isclose(
        objective_recomputed,
        solve_info.objective_value,
        rel_tol=OBJECTIVE_RELATIVE_TOLERANCE,
        abs_tol=OBJECTIVE_ABSOLUTE_TOLERANCE,
    ):
        violations.append(f"Objective difference {objective_difference:.6g} exceeds tolerance")

    return ValidationReport(
        passed=not violations,
        violations=violations,
        max_demand_absolute_difference=max_demand_difference,
        max_capacity_excess=max_capacity_excess,
        max_closed_facility_flow=max_closed_flow,
        minimum_shipment=minimum_shipment,
        max_binary_domain_distance=max_binary_distance,
        fixed_cost_recomputed=fixed_recomputed,
        transport_cost_recomputed=transport_recomputed,
        objective_recomputed=objective_recomputed,
        solver_objective=solve_info.objective_value,
        objective_absolute_difference=objective_difference,
    )


def assert_solution_valid(report: ValidationReport) -> None:
    if not report.passed:
        raise SolutionValidationError("; ".join(report.violations))
