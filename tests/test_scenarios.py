"""Scenario derivation, immutability, infeasibility, and CLI workflow tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pandas.testing as pdt
import pytest

import run_analysis as analysis_cli
from src.data_loader import (
    DataValidationError,
    ScenarioDefinition,
    ScenarioInfeasibleError,
    apply_scenario,
    assert_capacity_feasible,
    load_scenarios,
)
from src.scenario import derive_transport_costs


DEVELOPMENT_DIR = Path(__file__).resolve().parents[1]
SCENARIO_DATA_DIR = DEVELOPMENT_DIR / "data" / "scenario"


def test_transport_derivation_is_deterministic_and_matches_checked_in_matrix(base_data):
    rate = float(base_data.metadata["distance_rate_usd_per_unit_sdu"])
    decimals = int(float(base_data.metadata["transport_cost_rounding_decimals"]))

    first = derive_transport_costs(
        base_data.facilities,
        base_data.customers,
        distance_rate_usd_per_unit_sdu=rate,
        cost_decimals=decimals,
    )
    second = derive_transport_costs(
        base_data.facilities,
        base_data.customers,
        distance_rate_usd_per_unit_sdu=rate,
        cost_decimals=decimals,
    )

    pdt.assert_frame_equal(first, second)
    pdt.assert_frame_equal(
        first.reset_index(drop=True),
        base_data.transport_costs.reset_index(drop=True),
        check_dtype=False,
    )


def test_apply_scenario_scales_a_deep_copy_without_mutating_base(base_data):
    original = base_data.copy()
    scenario = ScenarioDefinition(
        scenario_id="IMMUTABILITY_CHECK",
        demand_multiplier=1.10,
        capacity_multiplier=0.90,
        fixed_cost_multiplier=1.20,
        transport_cost_multiplier=0.80,
    )

    scaled = apply_scenario(base_data, scenario)

    pdt.assert_frame_equal(base_data.facilities, original.facilities)
    pdt.assert_frame_equal(base_data.customers, original.customers)
    pdt.assert_frame_equal(base_data.transport_costs, original.transport_costs)
    assert base_data.metadata == original.metadata
    assert scaled is not base_data
    assert scaled.facilities is not base_data.facilities
    pdt.assert_series_equal(
        scaled.customers["demand_units_per_year"],
        original.customers["demand_units_per_year"] * 1.10,
    )
    pdt.assert_series_equal(
        scaled.facilities["capacity_units_per_year"],
        original.facilities["capacity_units_per_year"] * 0.90,
    )
    pdt.assert_series_equal(
        scaled.facilities["fixed_cost_usd_per_year"],
        original.facilities["fixed_cost_usd_per_year"] * 1.20,
    )
    pdt.assert_series_equal(
        scaled.transport_costs["unit_cost_usd_per_unit"],
        original.transport_costs["unit_cost_usd_per_unit"] * 0.80,
    )
    assert scaled.metadata["active_scenario"] == "IMMUTABILITY_CHECK"


def test_declared_infeasible_scenario_fails_controlled_capacity_gate(base_data):
    definitions = load_scenarios(SCENARIO_DATA_DIR / "scenarios.csv")
    scenario = next(item for item in definitions if item.scenario_id == "INFEASIBLE_DEMO")
    infeasible = apply_scenario(base_data, scenario)

    assert not scenario.expected_feasible
    assert not scenario.include_in_sensitivity
    assert infeasible.total_demand > infeasible.total_capacity
    with pytest.raises(ScenarioInfeasibleError, match="Insufficient total capacity"):
        assert_capacity_feasible(infeasible)


def test_scenario_definition_provenance_is_enforced(tmp_path):
    scenarios = pd.read_csv(SCENARIO_DATA_DIR / "scenarios.csv")
    scenarios.loc[scenarios.index[0], "provenance"] = "UNVERIFIED_SOURCE"
    invalid_path = tmp_path / "invalid_scenarios.csv"
    scenarios.to_csv(invalid_path, index=False)

    with pytest.raises(
        DataValidationError,
        match="scenarios.provenance contains unsupported label: UNVERIFIED_SOURCE",
    ):
        load_scenarios(invalid_path)

    with pytest.raises(
        DataValidationError,
        match="scenarios is missing required scenario_id: DEMAND_BASE",
    ):
        analysis_cli._required_scenario([], "DEMAND_BASE")


def test_zero_cost_capacity_and_demand_use_zero_safe_baseline_guards(
    tiny_data,
    tmp_path,
    monkeypatch,
):
    zero_case = tiny_data.copy()
    zero_case.customers["demand_units_per_year"] = 0.0
    zero_case.facilities["capacity_units_per_year"] = 0.0
    zero_case.facilities["fixed_cost_usd_per_year"] = 0.0
    zero_case.transport_costs["unit_cost_usd_per_unit"] = 0.0
    scenarios = [
        ScenarioDefinition(scenario_id="DEMAND_BASE"),
        ScenarioDefinition(
            scenario_id="INFEASIBLE_DEMO",
            expected_feasible=False,
            include_in_sensitivity=False,
        ),
    ]

    monkeypatch.setattr(analysis_cli, "load_network_data", lambda _path: zero_case.copy())
    monkeypatch.setattr(analysis_cli, "load_scenarios", lambda _path: scenarios)

    def controlled_capacity_check(data):
        if data.metadata.get("active_scenario") == "INFEASIBLE_DEMO":
            raise ScenarioInfeasibleError("Controlled test-only infeasibility")
        assert_capacity_feasible(data)

    monkeypatch.setattr(analysis_cli, "assert_capacity_feasible", controlled_capacity_check)
    for plot_name in [
        "plot_network",
        "plot_cost_breakdown",
        "plot_facility_utilization",
        "plot_sensitivity",
    ]:
        monkeypatch.setattr(analysis_cli, plot_name, lambda *args: args[-1])

    output_dir = tmp_path / "zero_case_outputs"
    summary = analysis_cli.run_analysis(SCENARIO_DATA_DIR, output_dir)

    assert summary["costs"]["objective_usd_per_year"] == pytest.approx(0.0)
    assert summary["baseline"]["objective_usd_per_year"] == pytest.approx(0.0)
    assert summary["baseline"]["scenario_cost_difference_usd_per_year"] == pytest.approx(0.0)
    assert summary["baseline"]["scenario_cost_reduction_relative_to_baseline"] == pytest.approx(0.0)
    assert summary["baseline"]["network_utilization"] == pytest.approx(0.0)

    baseline_summary = pd.read_csv(output_dir / "tables" / "baseline_summary.csv").iloc[0]
    assert baseline_summary["objective_usd_per_year"] == pytest.approx(0.0)
    assert baseline_summary["scenario_cost_reduction_relative_to_baseline"] == pytest.approx(0.0)
    assert baseline_summary["network_utilization"] == pytest.approx(0.0)


def test_one_command_analysis_emits_success_and_required_outputs(tmp_path):
    output_dir = tmp_path / "analysis_outputs"
    command = [
        sys.executable,
        str(DEVELOPMENT_DIR / "run_analysis.py"),
        "--data-dir",
        str(SCENARIO_DATA_DIR),
        "--output-dir",
        str(output_dir),
    ]
    completed = subprocess.run(
        command,
        cwd=DEVELOPMENT_DIR,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert "BUILD_STATUS=SUCCESS" in completed.stdout
    assert "TERMINATION=optimal" in completed.stdout
    assert f"OUTPUT_DIR={output_dir.resolve()}" in completed.stdout

    required_outputs = [
        "analysis_summary.json",
        "analysis_summary.md",
        "solver_info.json",
        "validation_report.json",
        "enumeration_validation.json",
        "tiny_known_case_validation.json",
        "infeasibility_demo.json",
        "kpis.json",
        "tables/facility_decisions.csv",
        "tables/active_shipments.csv",
        "tables/baseline_shipments.csv",
        "tables/baseline_summary.csv",
        "tables/cost_breakdown.csv",
        "tables/customer_service.csv",
        "tables/enumeration_results.csv",
        "tables/sensitivity_results.csv",
        "figures/optimized_network.png",
        "figures/cost_breakdown.png",
        "figures/facility_utilization.png",
        "figures/sensitivity_comparison.png",
    ]
    for relative_path in required_outputs:
        artifact = output_dir / relative_path
        assert artifact.is_file(), f"Missing output: {relative_path}"
        assert artifact.stat().st_size > 0, f"Empty output: {relative_path}"

    summary = json.loads((output_dir / "analysis_summary.json").read_text(encoding="utf-8"))
    assert summary["build_status"] == "SUCCESS"
    assert summary["network_dimensions"] == {
        "arcs": 72,
        "binary_variables": 6,
        "continuous_variables": 72,
        "customers": 12,
        "facilities": 6,
        "structural_constraints": 18,
    }
    assert summary["solver"]["termination_condition"] == "optimal"
    assert summary["figure_paths"] == [
        str(Path("figures") / "optimized_network.png"),
        str(Path("figures") / "cost_breakdown.png"),
        str(Path("figures") / "facility_utilization.png"),
        str(Path("figures") / "sensitivity_comparison.png"),
    ]
    assert all(not Path(path).is_absolute() for path in summary["figure_paths"])
    assert summary["validation_passed"]
    assert summary["enumeration_passed"]
    assert summary["tiny_known_case_passed"]
    assert summary["infeasibility_demo_passed"]
