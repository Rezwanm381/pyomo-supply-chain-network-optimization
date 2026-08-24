# Scenario data

## Disclosure

Every network input is synthetic or deterministically derived from a synthetic assumption. The dataset represents no real company, location, customer, freight rate, lane, or operating plan. Coordinates are schematic and must not be interpreted as latitude/longitude or placed on a real map. All financial outputs are scenario USD/year.

The base case is manually defined and deterministic. It contains no random generation, parameter search, or seed-dependent process. Without pre-build version history, the timing of input choices relative to the first diagnostic solve is not independently reconstructable.

## Base dimensions

| Item | Value |
|---|---:|
| Candidate facilities | 6 |
| Customer zones | 12 |
| Facility-customer arcs | 72 |
| Demand | 960 units/year |
| Potential capacity | 2,100 units/year |

## Files and schemas

### `scenario/facilities.csv`

Six candidate facilities. All rows are `SCENARIO_ASSUMPTION`.

| Field | Meaning | Unit/status |
|---|---|---|
| `facility_id` | Stable synthetic identifier | text |
| `facility_name` | Descriptive scenario label | text |
| `x_coord`, `y_coord` | Schematic planar coordinates | synthetic distance units (SDU) |
| `capacity_units_per_year` | Maximum annual flow when open | units/year |
| `fixed_cost_usd_per_year` | Annual opening cost | scenario USD/year |
| `provenance_label` | Input provenance | `SCENARIO_ASSUMPTION` |

### `scenario/customers.csv`

Twelve synthetic customer zones. All rows are `SCENARIO_ASSUMPTION`.

| Field | Meaning | Unit/status |
|---|---|---|
| `customer_id` | Stable synthetic identifier | text |
| `customer_name` | Descriptive scenario label | text |
| `x_coord`, `y_coord` | Schematic planar coordinates | SDU |
| `demand_units_per_year` | Exact annual demand | units/year |
| `provenance_label` | Input provenance | `SCENARIO_ASSUMPTION` |

### `scenario/transport_costs.csv`

The complete 6 × 12 arc matrix. Each facility-customer pair appears exactly once.

| Field | Meaning | Unit/status |
|---|---|---|
| `facility_id`, `customer_id` | Arc endpoints | identifiers from the entity tables |
| `distance_sdu` | Euclidean distance derived from schematic coordinates | SDU; `DERIVED_SCENARIO_VALUE` |
| `cost_usd_per_unit` | `round(distance_sdu × 3.20, 2)` | scenario USD/unit; `DERIVED_SCENARIO_VALUE` |
| `provenance_label` | Derived-field provenance | `DERIVED_SCENARIO_VALUE` |

Distances are calculated as \(\sqrt{(x_i-x_j)^2+(y_i-y_j)^2}\). They are schematic—not road mileage, time, or lane availability.

### `scenario/scenarios.csv`

Declared deterministic multipliers applied before each solve.

| Field | Meaning |
|---|---|
| `scenario_id` | Stable scenario label |
| `description` | Human-readable change |
| `demand_multiplier` | Multiplies every customer demand |
| `transport_cost_multiplier` | Multiplies every unit shipment cost |
| `fixed_cost_multiplier` | Multiplies every facility fixed cost |
| `capacity_multiplier` | Multiplies every facility capacity |
| `expected_feasible` | Declared feasibility expectation |
| `provenance_label` | `SCENARIO_ASSUMPTION` |

The eight reported cases are `DEMAND_LOW`, `DEMAND_BASE`, `DEMAND_HIGH`, `TRANSPORT_LOW`, `TRANSPORT_HIGH`, `FIXED_LOW`, `FIXED_HIGH`, and `CAPACITY_STRESS`. `INFEASIBLE_DEMO` is a controlled validation case and is not reported as an optimized sensitivity result.

### `scenario/scenario_metadata.csv`

Documents global assumptions and generation policy, including the annual planning horizon, Euclidean distance method, 3.20 scenario USD/(unit·SDU) rate, rounding convention, synthetic status, and absence of random generation.

## Validation

The loader checks required columns, unique and nonblank identifiers, finite nonnegative numeric values, known arc endpoints, complete arc coverage, and agreement between coordinates, distances, and derived unit costs. Scenario multipliers are validated after application. See `../docs/unit_conventions.md` and `../docs/reproducibility.md` for unit and execution details.
