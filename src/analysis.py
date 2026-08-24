"""Baseline, exhaustive enumeration, and sensitivity analysis."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.optimize import linprog

from .data_loader import (
    NetworkData,
    ScenarioDefinition,
    apply_scenario,
    assert_capacity_feasible,
)
from .model import build_model
from .solve import SolveInfo, solve_model
from .validation import (
    SolutionTables,
    ValidationReport,
    assert_solution_valid,
    extract_solution,
    validate_solution,
)


@dataclass
class SubsetSolution:
    open_facilities: tuple[str, ...]
    fixed_cost: float
    transport_cost: float
    total_cost: float
    shipments: pd.DataFrame


@dataclass
class EnumerationResult:
    best_solution: SubsetSolution
    subset_results: pd.DataFrame
    total_subsets: int
    feasible_subsets: int


@dataclass
class ScenarioRun:
    scenario: ScenarioDefinition
    data: NetworkData
    solve_info: SolveInfo
    validation: ValidationReport
    tables: SolutionTables


def solve_transport_subproblem(
    data: NetworkData,
    open_facilities: Iterable[str],
    *,
    tolerance: float = 1e-7,
) -> SubsetSolution | None:
    """Solve a fixed-network transportation LP independently with SciPy/HiGHS."""

    open_set = set(open_facilities)
    selected = tuple(facility for facility in data.facility_ids if facility in open_set)
    if not selected:
        if data.total_demand <= tolerance:
            return SubsetSolution(
                open_facilities=(),
                fixed_cost=0.0,
                transport_cost=0.0,
                total_cost=0.0,
                shipments=pd.DataFrame(
                    columns=[
                        "origin",
                        "destination",
                        "shipment_units_per_year",
                        "unit_cost_usd_per_unit",
                        "transport_cost_usd_per_year",
                    ]
                ),
            )
        return None
    facility_input = data.facilities.set_index("facility_id")
    customer_input = data.customers.set_index("customer_id")
    cost_input = data.transport_costs.set_index(["facility_id", "customer_id"])
    total_capacity = sum(float(facility_input.loc[f, "capacity_units_per_year"]) for f in selected)
    if total_capacity + tolerance < data.total_demand:
        return None

    facility_count = len(selected)
    customer_count = len(data.customer_ids)
    variable_count = facility_count * customer_count
    objective = np.array(
        [
            float(cost_input.loc[(facility, customer), "unit_cost_usd_per_unit"])
            for facility in selected
            for customer in data.customer_ids
        ],
        dtype=float,
    )
    demand_matrix = np.zeros((customer_count, variable_count), dtype=float)
    for customer_index in range(customer_count):
        for facility_index in range(facility_count):
            demand_matrix[customer_index, facility_index * customer_count + customer_index] = 1.0
    demand_rhs = np.array(
        [float(customer_input.loc[customer, "demand_units_per_year"]) for customer in data.customer_ids],
        dtype=float,
    )
    capacity_matrix = np.zeros((facility_count, variable_count), dtype=float)
    for facility_index in range(facility_count):
        start = facility_index * customer_count
        capacity_matrix[facility_index, start : start + customer_count] = 1.0
    capacity_rhs = np.array(
        [float(facility_input.loc[facility, "capacity_units_per_year"]) for facility in selected],
        dtype=float,
    )

    result = linprog(
        objective,
        A_ub=capacity_matrix,
        b_ub=capacity_rhs,
        A_eq=demand_matrix,
        b_eq=demand_rhs,
        bounds=(0.0, None),
        method="highs",
    )
    if result.status == 2:
        return None
    if not result.success:
        raise RuntimeError(
            f"Independent transportation LP failed for {selected}: status={result.status}, message={result.message}"
        )

    shipment_rows: list[dict[str, Any]] = []
    for facility_index, facility in enumerate(selected):
        for customer_index, customer in enumerate(data.customer_ids):
            shipment = float(result.x[facility_index * customer_count + customer_index])
            if shipment > tolerance:
                unit_cost = float(cost_input.loc[(facility, customer), "unit_cost_usd_per_unit"])
                shipment_rows.append(
                    {
                        "origin": facility,
                        "destination": customer,
                        "shipment_units_per_year": shipment,
                        "unit_cost_usd_per_unit": unit_cost,
                        "transport_cost_usd_per_year": shipment * unit_cost,
                    }
                )
    fixed_cost = sum(float(facility_input.loc[f, "fixed_cost_usd_per_year"]) for f in selected)
    transport_cost = float(result.fun)
    return SubsetSolution(
        open_facilities=selected,
        fixed_cost=fixed_cost,
        transport_cost=transport_cost,
        total_cost=fixed_cost + transport_cost,
        shipments=pd.DataFrame(
            shipment_rows,
            columns=[
                "origin",
                "destination",
                "shipment_units_per_year",
                "unit_cost_usd_per_unit",
                "transport_cost_usd_per_year",
            ],
        ),
    )


def enumerate_facility_subsets(data: NetworkData) -> EnumerationResult:
    """Enumerate every binary network and solve each feasible continuous LP."""

    facility_input = data.facilities.set_index("facility_id")
    result_rows: list[dict[str, Any]] = []
    feasible_solutions: list[SubsetSolution] = []
    for size in range(len(data.facility_ids) + 1):
        for subset in combinations(data.facility_ids, size):
            capacity = sum(float(facility_input.loc[f, "capacity_units_per_year"]) for f in subset)
            fixed_cost = sum(float(facility_input.loc[f, "fixed_cost_usd_per_year"]) for f in subset)
            if capacity + 1e-9 < data.total_demand:
                result_rows.append(
                    {
                        "open_facilities": ";".join(subset),
                        "facility_count": size,
                        "selected_capacity_units_per_year": capacity,
                        "status": "CAPACITY_INFEASIBLE",
                        "fixed_cost_usd_per_year": fixed_cost,
                        "transport_cost_usd_per_year": np.nan,
                        "total_cost_usd_per_year": np.nan,
                    }
                )
                continue
            solution = solve_transport_subproblem(data, subset)
            if solution is None:
                status = "LP_INFEASIBLE"
                transport_cost = np.nan
                total_cost = np.nan
            else:
                status = "FEASIBLE"
                transport_cost = solution.transport_cost
                total_cost = solution.total_cost
                feasible_solutions.append(solution)
            result_rows.append(
                {
                    "open_facilities": ";".join(subset),
                    "facility_count": size,
                    "selected_capacity_units_per_year": capacity,
                    "status": status,
                    "fixed_cost_usd_per_year": fixed_cost,
                    "transport_cost_usd_per_year": transport_cost,
                    "total_cost_usd_per_year": total_cost,
                }
            )

    if not feasible_solutions:
        raise RuntimeError("Enumeration found no feasible facility subset")
    best = min(feasible_solutions, key=lambda solution: (solution.total_cost, solution.open_facilities))
    return EnumerationResult(
        best_solution=best,
        subset_results=pd.DataFrame(result_rows),
        total_subsets=len(result_rows),
        feasible_subsets=len(feasible_solutions),
    )


def enumeration_agreement(
    tables: SolutionTables,
    solve_info: SolveInfo,
    enumeration: EnumerationResult,
    *,
    tolerance: float = 1e-5,
) -> dict[str, Any]:
    pyomo_open = tuple(tables.facilities.loc[tables.facilities["open"] == 1, "facility_id"].tolist())
    objective_difference = abs(solve_info.objective_value - enumeration.best_solution.total_cost)
    subset_key = ";".join(pyomo_open)
    subset_rows = enumeration.subset_results.loc[
        (enumeration.subset_results["open_facilities"] == subset_key)
        & (enumeration.subset_results["status"] == "FEASIBLE")
    ]
    pyomo_subset_separate_formulation_cost = (
        float(subset_rows["total_cost_usd_per_year"].iloc[0]) if not subset_rows.empty else None
    )
    subset_is_tied_optimum = (
        pyomo_subset_separate_formulation_cost is not None
        and abs(pyomo_subset_separate_formulation_cost - enumeration.best_solution.total_cost) <= tolerance
        and abs(pyomo_subset_separate_formulation_cost - solve_info.objective_value) <= tolerance
    )
    return {
        "passed": subset_is_tied_optimum and objective_difference <= tolerance,
        "pyomo_open_facilities": list(pyomo_open),
        "enumeration_open_facilities": list(enumeration.best_solution.open_facilities),
        "pyomo_objective_usd_per_year": solve_info.objective_value,
        "enumeration_objective_usd_per_year": enumeration.best_solution.total_cost,
        "pyomo_subset_separate_formulation_objective_usd_per_year": pyomo_subset_separate_formulation_cost,
        "pyomo_subset_is_objective_tied_optimum": subset_is_tied_optimum,
        "absolute_objective_difference": objective_difference,
        "objective_tolerance": tolerance,
        "total_subsets": enumeration.total_subsets,
        "feasible_subsets": enumeration.feasible_subsets,
        "formulation_comparison_method": "Separately assembled SciPy transportation formulation; shares the HiGHS solver engine",
    }


def compute_all_open_baseline(data: NetworkData) -> SubsetSolution:
    solution = solve_transport_subproblem(data, data.facility_ids)
    if solution is None:  # pragma: no cover - aggregate validation makes this defensive
        raise RuntimeError("ALL_FACILITIES_OPEN baseline is unexpectedly infeasible")
    return solution


def run_sensitivity_analysis(
    base_data: NetworkData,
    scenarios: list[ScenarioDefinition],
    *,
    solver_name: str = "appsi_highs",
) -> tuple[pd.DataFrame, dict[str, ScenarioRun]]:
    """Run only the compact, predeclared feasible sensitivity scenarios."""

    rows: list[dict[str, Any]] = []
    runs: dict[str, ScenarioRun] = {}
    for scenario in scenarios:
        if not scenario.include_in_sensitivity:
            continue
        scenario_data = apply_scenario(base_data, scenario)
        assert_capacity_feasible(scenario_data)
        model = build_model(scenario_data)
        solve_info = solve_model(model, solver_name=solver_name)
        validation = validate_solution(model, scenario_data, solve_info)
        assert_solution_valid(validation)
        tables = extract_solution(model, scenario_data, solve_info)
        runs[scenario.scenario_id] = ScenarioRun(scenario, scenario_data, solve_info, validation, tables)
        opened = tables.facilities.loc[tables.facilities["open"] == 1, "facility_id"].tolist()
        binding = tables.facilities.loc[tables.facilities["capacity_binding"], "facility_id"].tolist()
        rows.append(
            {
                "scenario_id": scenario.scenario_id,
                "description": scenario.description,
                "demand_multiplier": scenario.demand_multiplier,
                "capacity_multiplier": scenario.capacity_multiplier,
                "fixed_cost_multiplier": scenario.fixed_cost_multiplier,
                "transport_cost_multiplier": scenario.transport_cost_multiplier,
                "objective_usd_per_year": solve_info.objective_value,
                "fixed_cost_usd_per_year": tables.kpis["fixed_cost_usd_per_year"],
                "transport_cost_usd_per_year": tables.kpis["transport_cost_usd_per_year"],
                "facilities_opened": len(opened),
                "open_facilities": ";".join(opened),
                "binding_facilities": ";".join(binding),
                "network_utilization": tables.kpis["network_utilization"],
                "maximum_open_facility_utilization": tables.kpis["maximum_open_facility_utilization"],
                "unused_selected_capacity_units_per_year": tables.kpis[
                    "unused_selected_capacity_units_per_year"
                ],
                "total_demand_units_per_year": scenario_data.total_demand,
                "solver_status": solve_info.solver_status,
                "termination_condition": solve_info.termination_condition,
                "validation_passed": validation.passed,
            }
        )

    summary = pd.DataFrame(rows)
    if "DEMAND_BASE" not in runs:
        raise RuntimeError("Sensitivity definitions must include DEMAND_BASE")
    base_configuration = summary.loc[summary["scenario_id"] == "DEMAND_BASE", "open_facilities"].iloc[0]
    summary["configuration_changed_from_base"] = summary["open_facilities"] != base_configuration
    return summary, runs
