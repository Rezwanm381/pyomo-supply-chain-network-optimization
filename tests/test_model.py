"""Tests for the Pyomo formulation itself."""

from __future__ import annotations

import pytest
from pyomo.environ import Var, minimize, value

from src.model import build_model


def test_variable_domains_counts_and_structural_counts(tiny_data):
    model = build_model(tiny_data)

    binary_variables = list(model.open_facility.values())
    shipment_variables = list(model.shipment.values())
    all_variables = list(model.component_data_objects(Var, active=True))

    assert len(binary_variables) == 2
    assert len(shipment_variables) == 4
    assert len(all_variables) == 6
    assert all(variable.is_binary() for variable in binary_variables)
    assert all(variable.is_continuous() for variable in shipment_variables)
    assert all(variable.lb == 0 and variable.ub is None for variable in shipment_variables)
    assert len(model.demand_balance) == 2
    assert len(model.facility_capacity) == 2
    assert model.total_cost.sense == minimize


def test_demand_and_capacity_rows_encode_the_documented_formulation(tiny_data):
    model = build_model(tiny_data)
    known_shipments = {
        ("A", "C1"): 40.0,
        ("A", "C2"): 0.0,
        ("B", "C1"): 0.0,
        ("B", "C2"): 40.0,
    }
    for facility in model.F:
        model.open_facility[facility].set_value(1.0)
    for arc, shipment in known_shipments.items():
        model.shipment[arc].set_value(shipment)

    for customer in model.C:
        constraint = model.demand_balance[customer]
        assert constraint.equality
        assert value(constraint.body) == pytest.approx(value(model.demand[customer]))

    for facility in model.F:
        constraint = model.facility_capacity[facility]
        assert value(constraint.body) <= value(constraint.upper) + 1e-9


def test_capacity_link_makes_positive_flow_from_closed_facility_infeasible(tiny_data):
    model = build_model(tiny_data)
    model.open_facility["A"].set_value(0.0)
    model.shipment["A", "C1"].set_value(1.0)
    model.shipment["A", "C2"].set_value(0.0)

    capacity_row = model.facility_capacity["A"]
    assert value(capacity_row.body) > value(capacity_row.upper)

    model.shipment["A", "C1"].set_value(0.0)
    assert value(capacity_row.body) <= value(capacity_row.upper)
