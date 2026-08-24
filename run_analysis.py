"""One-command reproducible optimization analysis."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any

DEVELOPMENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = DEVELOPMENT_DIR.parent
os.environ.setdefault("MPLCONFIGDIR", str(DEVELOPMENT_DIR / ".cache" / "matplotlib"))

import pandas as pd  # noqa: E402

from src.analysis import (  # noqa: E402
    compute_all_open_baseline,
    enumerate_facility_subsets,
    enumeration_agreement,
    run_sensitivity_analysis,
)
from src.data_loader import (  # noqa: E402
    DataValidationError,
    ScenarioDefinition,
    ScenarioInfeasibleError,
    apply_scenario,
    assert_capacity_feasible,
    load_network_data,
    load_scenarios,
)
from src.model import build_model  # noqa: E402
from src.scenario import make_tiny_known_case  # noqa: E402
from src.solve import solve_model  # noqa: E402
from src.validation import (  # noqa: E402
    assert_solution_valid,
    extract_solution,
    validate_solution,
)
from src.visualization import (  # noqa: E402
    plot_cost_breakdown,
    plot_facility_utilization,
    plot_network,
    plot_sensitivity,
)


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, default=_json_default)
        handle.write("\n")


def _required_scenario(
    scenarios: list[ScenarioDefinition],
    scenario_id: str,
) -> ScenarioDefinition:
    """Return a required scenario or raise a clear input-contract error."""

    for scenario in scenarios:
        if scenario.scenario_id == scenario_id:
            return scenario
    raise DataValidationError(f"scenarios is missing required scenario_id: {scenario_id}")


def _write_analysis_summary(
    path: Path,
    *,
    solver_name: str,
    solver_version: str,
    solver_status: str,
    termination_condition: str,
    objective: float,
    selected: list[str],
    fixed_cost: float,
    transport_cost: float,
    baseline_objective: float,
    baseline_difference: float,
    baseline_percent: float,
    baseline_network_utilization: float,
    enumeration_passed: bool,
    sensitivity: pd.DataFrame,
) -> None:
    sensitivity_rows = "\n".join(
        f"| {row.scenario_id} | {row.objective_usd_per_year:,.3f} | {row.open_facilities} | {str(bool(row.configuration_changed_from_base)).upper()} |"
        for row in sensitivity.itertuples(index=False)
    )
    content = f"""# Generated analysis summary

All financial values are scenario costs for one annual horizon.

- Solver interface: {solver_name}
- Solver engine version: {solver_version}
- Solver status: {solver_status}
- Termination condition: {termination_condition}
- Objective: {objective:,.2f} scenario USD/year
- Selected facilities: {', '.join(selected)}
- Fixed-cost component: {fixed_cost:,.2f}
- Transport-cost component: {transport_cost:,.2f}
- All-facilities-open baseline: {baseline_objective:,.2f}
- Scenario cost reduction relative to the defined all-facilities-open reference: {baseline_difference:,.2f} ({baseline_percent:.4%}); not realized savings
- Baseline network utilization: {baseline_network_utilization:.4%}
- Enumeration agreement: {str(enumeration_passed).upper()}

| Scenario | Objective | Open facilities | Configuration changed from base |
|---|---:|---|---|
{sensitivity_rows}
"""
    path.write_text(content, encoding="utf-8")


def run_analysis(data_dir: Path, output_dir: Path, solver_name: str = "appsi_highs") -> dict[str, Any]:
    """Execute the complete optimization and validation pipeline."""

    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    base_inputs = load_network_data(data_dir)
    scenarios = load_scenarios(data_dir / "scenarios.csv")
    base_definition = _required_scenario(scenarios, "DEMAND_BASE")
    base_data = apply_scenario(base_inputs, base_definition)
    assert_capacity_feasible(base_data)

    model = build_model(base_data)
    solve_info = solve_model(model, solver_name=solver_name)
    validation = validate_solution(model, base_data, solve_info)
    assert_solution_valid(validation)
    tables = extract_solution(model, base_data, solve_info)

    enumeration = enumerate_facility_subsets(base_data)
    enumeration_check = enumeration_agreement(tables, solve_info, enumeration)
    if not enumeration_check["passed"]:
        raise RuntimeError(f"Enumeration disagrees with the Pyomo MILP: {enumeration_check}")

    baseline = compute_all_open_baseline(base_data)
    baseline_difference = baseline.total_cost - solve_info.objective_value
    baseline_percent = baseline_difference / baseline.total_cost if baseline.total_cost > 0 else 0.0
    baseline_network_utilization = (
        base_data.total_demand / base_data.total_capacity if base_data.total_capacity > 0 else 0.0
    )

    sensitivity, sensitivity_runs = run_sensitivity_analysis(
        base_inputs,
        scenarios,
        solver_name=solver_name,
    )

    infeasible_definition = _required_scenario(scenarios, "INFEASIBLE_DEMO")
    infeasible_data = apply_scenario(base_inputs, infeasible_definition)
    try:
        assert_capacity_feasible(infeasible_data)
    except ScenarioInfeasibleError as exc:
        infeasibility_demo = {
            "passed": True,
            "scenario_id": infeasible_definition.scenario_id,
            "expected_status": "PRE_SOLVE_INFEASIBLE",
            "observed_status": "PRE_SOLVE_INFEASIBLE",
            "total_demand_units_per_year": infeasible_data.total_demand,
            "total_capacity_units_per_year": infeasible_data.total_capacity,
            "message": str(exc),
        }
    else:  # pragma: no cover - fixed input should always trigger this gate
        raise RuntimeError("Controlled infeasible scenario did not fail its capacity precheck")

    tiny_data = make_tiny_known_case()
    tiny_model = build_model(tiny_data)
    tiny_solve = solve_model(tiny_model, solver_name=solver_name)
    tiny_validation = validate_solution(tiny_model, tiny_data, tiny_solve)
    assert_solution_valid(tiny_validation)
    tiny_tables = extract_solution(tiny_model, tiny_data, tiny_solve)
    tiny_enumeration = enumerate_facility_subsets(tiny_data)
    tiny_agreement = enumeration_agreement(tiny_tables, tiny_solve, tiny_enumeration)
    tiny_selected = tiny_tables.facilities.loc[tiny_tables.facilities["open"] == 1, "facility_id"].tolist()
    tiny_passed = (
        math.isclose(tiny_solve.objective_value, 280.0, rel_tol=0.0, abs_tol=1e-6)
        and tiny_selected == ["A", "B"]
        and tiny_agreement["passed"]
    )
    if not tiny_passed:
        raise RuntimeError("Tiny known-case regression did not reproduce the manual optimum of 280")
    tiny_case_result = {
        "passed": tiny_passed,
        "manual_expected_objective": 280.0,
        "solver_objective": tiny_solve.objective_value,
        "selected_facilities": tiny_selected,
        "enumeration_agreement": tiny_agreement,
        "validation": tiny_validation.to_dict(),
    }

    tables.facilities.to_csv(tables_dir / "facility_decisions.csv", index=False, float_format="%.6f")
    tables.shipments.to_csv(tables_dir / "active_shipments.csv", index=False, float_format="%.6f")
    tables.customers.to_csv(tables_dir / "customer_service.csv", index=False, float_format="%.6f")
    tables.cost_breakdown.to_csv(tables_dir / "cost_breakdown.csv", index=False, float_format="%.6f")
    enumeration.subset_results.to_csv(tables_dir / "enumeration_results.csv", index=False, float_format="%.6f")
    baseline.shipments.to_csv(tables_dir / "baseline_shipments.csv", index=False, float_format="%.6f")
    sensitivity.to_csv(tables_dir / "sensitivity_results.csv", index=False, float_format="%.6f")
    pd.DataFrame(
        [
            {
                "baseline_id": "ALL_FACILITIES_OPEN",
                "definition": "All six facility binaries fixed open; shipment allocation minimizes transport cost",
                "facility_count": len(base_data.facility_ids),
                "fixed_cost_usd_per_year": baseline.fixed_cost,
                "transport_cost_usd_per_year": baseline.transport_cost,
                "objective_usd_per_year": baseline.total_cost,
                "optimized_objective_usd_per_year": solve_info.objective_value,
                "scenario_cost_difference_usd_per_year": baseline_difference,
                "scenario_cost_reduction_relative_to_baseline": baseline_percent,
                "network_utilization": baseline_network_utilization,
            }
        ]
    ).to_csv(tables_dir / "baseline_summary.csv", index=False, float_format="%.6f")

    _write_json(output_dir / "solver_info.json", solve_info.to_dict())
    _write_json(output_dir / "validation_report.json", validation.to_dict())
    _write_json(output_dir / "kpis.json", tables.kpis)
    _write_json(output_dir / "enumeration_validation.json", enumeration_check)
    _write_json(output_dir / "tiny_known_case_validation.json", tiny_case_result)
    _write_json(output_dir / "infeasibility_demo.json", infeasibility_demo)

    figure_paths = [
        plot_network(base_data, tables.facilities, tables.shipments, figures_dir / "optimized_network.png"),
        plot_cost_breakdown(
            float(tables.kpis["fixed_cost_usd_per_year"]),
            float(tables.kpis["transport_cost_usd_per_year"]),
            baseline.fixed_cost,
            baseline.transport_cost,
            figures_dir / "cost_breakdown.png",
        ),
        plot_facility_utilization(tables.facilities, figures_dir / "facility_utilization.png"),
        plot_sensitivity(sensitivity, figures_dir / "sensitivity_comparison.png"),
    ]

    selected = tables.facilities.loc[tables.facilities["open"] == 1, "facility_id"].tolist()
    summary = {
        "build_status": "SUCCESS",
        "public_framing": "SCENARIO_BASED_OPTIMIZATION_CASE_STUDY",
        "scenario_name": base_data.metadata.get("scenario_name"),
        "network_dimensions": {
            "facilities": len(base_data.facility_ids),
            "customers": len(base_data.customer_ids),
            "arcs": len(base_data.transport_costs),
            "continuous_variables": len(base_data.transport_costs),
            "binary_variables": len(base_data.facility_ids),
            "structural_constraints": len(base_data.facility_ids) + len(base_data.customer_ids),
        },
        "solver": solve_info.to_dict(),
        "selected_facilities": selected,
        "costs": {
            "fixed_cost_usd_per_year": tables.kpis["fixed_cost_usd_per_year"],
            "transport_cost_usd_per_year": tables.kpis["transport_cost_usd_per_year"],
            "objective_usd_per_year": solve_info.objective_value,
        },
        "baseline": {
            "definition": "ALL_FACILITIES_OPEN",
            "objective_usd_per_year": baseline.total_cost,
            "scenario_cost_difference_usd_per_year": baseline_difference,
            "scenario_cost_reduction_relative_to_baseline": baseline_percent,
            "network_utilization": baseline_network_utilization,
        },
        "validation_passed": validation.passed,
        "enumeration_passed": enumeration_check["passed"],
        "tiny_known_case_passed": tiny_passed,
        "infeasibility_demo_passed": infeasibility_demo["passed"],
        "sensitivity_scenarios": sensitivity["scenario_id"].tolist(),
        "figure_paths": [str(path.relative_to(output_dir)) for path in figure_paths],
    }
    _write_json(output_dir / "analysis_summary.json", summary)
    _write_analysis_summary(
        output_dir / "analysis_summary.md",
        solver_name=solve_info.solver_name,
        solver_version=solve_info.solver_version,
        solver_status=solve_info.solver_status,
        termination_condition=solve_info.termination_condition,
        objective=solve_info.objective_value,
        selected=selected,
        fixed_cost=float(tables.kpis["fixed_cost_usd_per_year"]),
        transport_cost=float(tables.kpis["transport_cost_usd_per_year"]),
        baseline_objective=baseline.total_cost,
        baseline_difference=baseline_difference,
        baseline_percent=baseline_percent,
        baseline_network_utilization=baseline_network_utilization,
        enumeration_passed=bool(enumeration_check["passed"]),
        sensitivity=sensitivity,
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEVELOPMENT_DIR / "data" / "scenario",
        help="Directory containing the scenario CSV inputs",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEVELOPMENT_DIR / ".private_outputs" / "module_7_25C",
        help="Directory for generated tables, figures, and checks",
    )
    parser.add_argument("--solver", default="appsi_highs", help="Pyomo solver interface")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_analysis(args.data_dir.resolve(), args.output_dir.resolve(), args.solver)
    solver = summary["solver"]
    print("BUILD_STATUS=SUCCESS")
    print(f"SOLVER={solver['solver_name']} {solver['solver_version']}")
    print(f"TERMINATION={solver['termination_condition']}")
    print(f"OBJECTIVE={solver['objective_value']:.2f}")
    print(f"SELECTED_FACILITIES={','.join(summary['selected_facilities'])}")
    print(f"OUTPUT_DIR={args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
