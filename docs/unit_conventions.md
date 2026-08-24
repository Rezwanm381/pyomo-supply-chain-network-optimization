# Unit conventions

## Planning horizon

The model uses one annual scenario horizon. Demand, capacity, shipment, fixed costs, and the objective are all normalized to that same horizon. No monthly costs are mixed with annual costs.

| Symbol or field | Meaning | Unit | Provenance label |
|---|---|---|---|
| `x_coord_sdu`, `y_coord_sdu` | Schematic coordinate | synthetic distance units (SDU) | SCENARIO_ASSUMPTION |
| `distance_sdu` | Euclidean distance between synthetic coordinates | SDU | DERIVED_SCENARIO_VALUE |
| `demand_units_per_year`, \(d_j\) | Customer demand | scenario units/year | SCENARIO_ASSUMPTION |
| `capacity_units_per_year`, \(K_i\) | Facility throughput capacity | scenario units/year | SCENARIO_ASSUMPTION |
| `shipment_units_per_year`, \(x_{ij}\) | Assigned shipment flow | scenario units/year | MODEL_DECISION |
| `fixed_cost_usd_per_year`, \(f_i\) | Facility opening cost for the horizon | USD/year | SCENARIO_ASSUMPTION |
| `distance_rate_usd_per_unit_sdu` | Distance-based shipment-cost rate | USD/(unit·SDU) | SCENARIO_ASSUMPTION |
| `unit_cost_usd_per_unit`, \(c_{ij}\) | Distance-based shipment cost | USD/unit | DERIVED_SCENARIO_VALUE |
| fixed-cost component | \(\sum_i f_i y_i\) | USD/year | MODEL_RESULT |
| transport-cost component | \(\sum_{ij} c_{ij}x_{ij}\) | USD/year | MODEL_RESULT |
| total objective, \(Z\) | Total annual scenario cost | USD/year | MODEL_RESULT |
| utilization | assigned flow divided by open capacity | dimensionless ratio | MODEL_RESULT |

## Transport-cost convention

For each facility-customer pair:

\[
\text{distance}_{ij}=\sqrt{(x_i-x_j)^2+(y_i-y_j)^2},
\]

\[
c_{ij}=r\,\text{distance}_{ij},
\]

where \(r=3.20\) scenario USD/(unit·SDU). Costs are calculated from unrounded distance and rounded once to two decimal places in the input file. Euclidean distance is a schematic proxy, not road mileage, route time, or a sourced freight quote.

## Interpretation boundary

Every financial result is a `SCENARIO_COST`. It must not be described as an actual cost, audited logistics expense, realized saving, or verified company outcome.
