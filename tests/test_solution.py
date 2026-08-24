"""Solver, post-solve validation, and enumeration tests."""

from __future__ import annotations

import pandas as pd
import pytest
from pyomo.environ import (
    ConcreteModel,
    Constraint,
    NonNegativeReals,
    Objective,
    Reals,
    Var,
    value,
)

from src.analysis import (
    compute_all_open_baseline,
    enumerate_facility_subsets,
    enumeration_agreement,
    solve_transport_subproblem,
)
from src.model import build_model
from src.solve import InfeasibleModelError, SolveInfo, UnboundedModelError, solve_model
from src.validation import SolutionTables, extract_solution, validate_solution


def test_tiny_case_has_solver_certified_manual_optimum_of_280(solved_tiny):
    data, model, solve_info = solved_tiny
    tables = extract_solution(model, data, solve_info)

    assert solve_info.solver_status == "ok"
    assert solve_info.termination_condition == "optimal"
    assert solve_info.objective_value == pytest.approx(280.0, abs=1e-6)
    assert solve_info.best_bound == pytest.approx(280.0, abs=1e-6)
    assert solve_info.relative_mip_gap == pytest.approx(0.0, abs=1e-12)

    opened = tables.facilities.loc[tables.facilities["open"] == 1, "facility_id"].tolist()
    shipments = {
        (row.origin, row.destination): row.shipment_units_per_year
        for row in tables.shipments.itertuples(index=False)
    }
    assert opened == ["A", "B"]
    assert shipments == pytest.approx({("A", "C1"): 40.0, ("B", "C2"): 40.0})
    assert tables.kpis["fixed_cost_usd_per_year"] == pytest.approx(160.0)
    assert tables.kpis["transport_cost_usd_per_year"] == pytest.approx(120.0)


def test_independent_checks_confirm_constraints_and_objective(solved_tiny):
    data, model, solve_info = solved_tiny
    report = validate_solution(model, data, solve_info)
    facility_input = data.facilities.set_index("facility_id")
    customer_input = data.customers.set_index("customer_id")

    for customer in data.customer_ids:
        delivered = sum(value(model.shipment[facility, customer]) for facility in data.facility_ids)
        assert delivered == pytest.approx(
            customer_input.loc[customer, "demand_units_per_year"], abs=1e-7
        )
    for facility in data.facility_ids:
        assigned = sum(value(model.shipment[facility, customer]) for customer in data.customer_ids)
        enabled_capacity = (
            facility_input.loc[facility, "capacity_units_per_year"]
            * value(model.open_facility[facility])
        )
        assert assigned <= enabled_capacity + 1e-7

    assert report.passed
    assert report.violations == []
    assert report.max_demand_absolute_difference <= report.feasibility_tolerance
    assert report.max_capacity_excess <= report.feasibility_tolerance
    assert report.max_closed_facility_flow <= report.feasibility_tolerance
    assert report.minimum_shipment >= -report.feasibility_tolerance
    assert report.objective_recomputed == pytest.approx(280.0, abs=1e-6)
    assert report.objective_absolute_difference <= report.objective_absolute_tolerance


def test_independent_validator_rejects_corrupted_closed_facility_solution(solved_tiny):
    data, model, solve_info = solved_tiny
    model.open_facility["A"].set_value(0.0)

    report = validate_solution(model, data, solve_info)

    assert not report.passed
    assert report.max_closed_facility_flow == pytest.approx(40.0)
    assert report.max_capacity_excess == pytest.approx(40.0)
    assert report.objective_absolute_difference == pytest.approx(100.0)
    assert any("Closed-facility flow" in violation for violation in report.violations)
    assert any("Objective difference" in violation for violation in report.violations)


def test_optimized_network_sends_zero_flow_from_a_closed_facility(tiny_data):
    one_facility_data = tiny_data.copy()
    one_facility_data.facilities.loc[
        one_facility_data.facilities["facility_id"] == "A",
        "fixed_cost_usd_per_year",
    ] = 10_000.0
    model = build_model(one_facility_data)
    solve_info = solve_model(model)

    assert solve_info.termination_condition == "optimal"
    assert value(model.open_facility["A"]) == pytest.approx(0.0, abs=1e-7)
    assert sum(value(model.shipment["A", customer]) for customer in model.C) == pytest.approx(
        0.0, abs=1e-7
    )
    assert value(model.open_facility["B"]) == pytest.approx(1.0, abs=1e-7)


def test_tiny_case_enumeration_agrees_with_pyomo(solved_tiny):
    data, model, solve_info = solved_tiny
    tables = extract_solution(model, data, solve_info)
    enumeration = enumerate_facility_subsets(data)
    agreement = enumeration_agreement(tables, solve_info, enumeration)

    assert enumeration.total_subsets == 4
    assert enumeration.feasible_subsets == 3
    assert enumeration.best_solution.open_facilities == ("A", "B")
    assert enumeration.best_solution.total_cost == pytest.approx(280.0, abs=1e-6)
    assert agreement["passed"]
    assert agreement["absolute_objective_difference"] <= agreement["objective_tolerance"]


def test_infeasible_termination_raises_controlled_error_before_solution_loading():
    model = ConcreteModel()
    model.x = Var(domain=NonNegativeReals)
    model.impossible = Constraint(expr=model.x <= -1.0)
    model.total_cost = Objective(expr=model.x)

    with pytest.raises(InfeasibleModelError, match="termination condition: infeasible"):
        solve_model(model)


def test_unbounded_termination_raises_controlled_error_before_solution_loading():
    model = ConcreteModel()
    model.x = Var(domain=Reals)
    model.total_cost = Objective(expr=-model.x)

    with pytest.raises(UnboundedModelError, match="termination condition: unbounded"):
        solve_model(model)


def test_zero_total_demand_extracts_empty_shipments_and_zero_safe_kpis(tiny_data):
    zero_demand = tiny_data.copy()
    zero_demand.customers["demand_units_per_year"] = 0.0
    model = build_model(zero_demand)
    solve_info = solve_model(model)
    tables = extract_solution(model, zero_demand, solve_info)
    report = validate_solution(model, zero_demand, solve_info)
    enumeration = enumerate_facility_subsets(zero_demand)

    assert solve_info.objective_value == pytest.approx(0.0, abs=1e-7)
    assert tables.shipments.empty
    assert tables.shipments.columns.tolist() == [
        "origin",
        "origin_name",
        "destination",
        "destination_name",
        "shipment_units_per_year",
        "distance_sdu",
        "unit_cost_usd_per_unit",
        "transport_cost_usd_per_year",
    ]
    assert tables.facilities["open"].sum() == 0
    assert tables.kpis["average_open_facility_utilization"] == pytest.approx(0.0)
    assert tables.kpis["network_utilization"] == pytest.approx(0.0)
    assert tables.kpis["maximum_open_facility_utilization"] == pytest.approx(0.0)
    assert tables.kpis["demand_served_units_per_year"] == pytest.approx(0.0)
    assert report.passed
    assert enumeration.best_solution.open_facilities == ()
    assert enumeration.best_solution.total_cost == pytest.approx(0.0)
    assert enumeration.best_solution.shipments.empty


def test_zero_demand_nonempty_subset_and_baseline_keep_shipment_csv_schema(
    tiny_data,
    tmp_path,
):
    zero_demand = tiny_data.copy()
    zero_demand.customers["demand_units_per_year"] = 0.0
    expected_columns = [
        "origin",
        "destination",
        "shipment_units_per_year",
        "unit_cost_usd_per_unit",
        "transport_cost_usd_per_year",
    ]

    nonempty_subset = solve_transport_subproblem(zero_demand, ["A"])
    baseline = compute_all_open_baseline(zero_demand)

    assert nonempty_subset is not None
    assert nonempty_subset.open_facilities == ("A",)
    assert baseline.open_facilities == ("A", "B")
    for name, solution in [("subset", nonempty_subset), ("baseline", baseline)]:
        assert solution.shipments.empty
        assert solution.shipments.columns.tolist() == expected_columns
        csv_path = tmp_path / f"{name}_shipments.csv"
        solution.shipments.to_csv(csv_path, index=False)
        assert pd.read_csv(csv_path).columns.tolist() == expected_columns


def test_enumeration_agreement_accepts_a_distinct_objective_tied_subset(tiny_data):
    tied_data = tiny_data.copy()
    tied_data.facilities["capacity_units_per_year"] = 1.0
    tied_data.facilities["fixed_cost_usd_per_year"] = 10.0
    tied_data.customers["demand_units_per_year"] = [1.0, 0.0]
    tied_data.transport_costs["unit_cost_usd_per_unit"] = 0.0
    enumeration = enumerate_facility_subsets(tied_data)

    tables = SolutionTables(
        facilities=pd.DataFrame(
            [
                {"facility_id": "A", "open": 0},
                {"facility_id": "B", "open": 1},
            ]
        ),
        shipments=pd.DataFrame(),
        customers=pd.DataFrame(),
        cost_breakdown=pd.DataFrame(),
        kpis={},
    )
    solve_info = SolveInfo(
        solver_name="TEST_DOUBLE",
        solver_version="N/A",
        solver_status="ok",
        termination_condition="optimal",
        objective_value=10.0,
        best_bound=10.0,
        relative_mip_gap=0.0,
        solve_seconds=0.0,
    )

    agreement = enumeration_agreement(tables, solve_info, enumeration)

    assert enumeration.best_solution.open_facilities == ("A",)
    assert agreement["pyomo_open_facilities"] == ["B"]
    assert agreement["enumeration_open_facilities"] == ["A"]
    assert agreement["pyomo_subset_separate_formulation_objective_usd_per_year"] == pytest.approx(10.0)
    assert agreement["pyomo_subset_is_objective_tied_optimum"]
    assert agreement["passed"]
