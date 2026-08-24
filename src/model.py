"""Clean-room Pyomo facility-location model."""

from __future__ import annotations

from pyomo.environ import (
    Binary,
    ConcreteModel,
    Constraint,
    Expression,
    NonNegativeReals,
    Objective,
    Param,
    Set,
    Var,
    minimize,
)

from .data_loader import NetworkData, validate_network_data


def build_model(data: NetworkData) -> ConcreteModel:
    """Build a validated single-period capacitated facility-location MILP."""

    validate_network_data(data, require_capacity=True)
    facilities = data.facility_ids
    customers = data.customer_ids
    facility_table = data.facilities.set_index("facility_id")
    customer_table = data.customers.set_index("customer_id")
    transport_table = data.transport_costs.set_index(["facility_id", "customer_id"])

    model = ConcreteModel(name="CleanRoomDistributionNetworkDesign")
    model.F = Set(initialize=facilities, ordered=True, doc="Candidate facilities")
    model.C = Set(initialize=customers, ordered=True, doc="Customer zones")

    model.capacity = Param(
        model.F,
        initialize={facility: float(facility_table.loc[facility, "capacity_units_per_year"]) for facility in facilities},
        within=NonNegativeReals,
        doc="Facility capacity in units/year",
    )
    model.fixed_cost = Param(
        model.F,
        initialize={facility: float(facility_table.loc[facility, "fixed_cost_usd_per_year"]) for facility in facilities},
        within=NonNegativeReals,
        doc="Facility fixed cost in USD/year",
    )
    model.demand = Param(
        model.C,
        initialize={customer: float(customer_table.loc[customer, "demand_units_per_year"]) for customer in customers},
        within=NonNegativeReals,
        doc="Customer demand in units/year",
    )
    model.unit_cost = Param(
        model.F,
        model.C,
        initialize={
            (facility, customer): float(transport_table.loc[(facility, customer), "unit_cost_usd_per_unit"])
            for facility in facilities
            for customer in customers
        },
        within=NonNegativeReals,
        doc="Shipment cost in USD/unit",
    )

    model.open_facility = Var(model.F, domain=Binary, doc="1 if facility opens")
    model.shipment = Var(model.F, model.C, domain=NonNegativeReals, doc="Shipment in units/year")

    def demand_balance_rule(active_model: ConcreteModel, customer: str):
        return sum(active_model.shipment[facility, customer] for facility in active_model.F) == active_model.demand[customer]

    model.demand_balance = Constraint(model.C, rule=demand_balance_rule)

    def capacity_rule(active_model: ConcreteModel, facility: str):
        return sum(active_model.shipment[facility, customer] for customer in active_model.C) <= (
            active_model.capacity[facility] * active_model.open_facility[facility]
        )

    model.facility_capacity = Constraint(model.F, rule=capacity_rule)
    model.fixed_cost_component = Expression(
        expr=sum(model.fixed_cost[facility] * model.open_facility[facility] for facility in model.F)
    )
    model.transport_cost_component = Expression(
        expr=sum(
            model.unit_cost[facility, customer] * model.shipment[facility, customer]
            for facility in model.F
            for customer in model.C
        )
    )
    model.total_cost = Objective(
        expr=model.fixed_cost_component + model.transport_cost_component,
        sense=minimize,
    )
    return model

