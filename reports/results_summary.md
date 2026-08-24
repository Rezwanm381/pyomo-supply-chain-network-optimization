# Results summary

All financial values below are annual `SCENARIO_COSTS` for the synthetic case.

## Solver result

| Item | Result |
|---|---|
| Pyomo version | 6.10.1 |
| Solver | `appsi_highs` / HiGHS 1.15.1 |
| Solver status | `ok` |
| Termination condition | `optimal` |
| Best bound | 285,488.90 |
| Final relative MIP gap | 0.0 |
| Objective | 285,488.90 scenario USD/year |
| Facilities selected | `FAC_NW`, `FAC_NE`, `FAC_SE` |

## Facility decisions

| Facility | Open | Capacity | Assigned flow | Utilization | Unused capacity | Fixed cost |
|---|---:|---:|---:|---:|---:|---:|
| FAC_NW | 1 | 330 | 330 | 100.000% | 0 | 74,000 |
| FAC_SW | 0 | 300 | 0 | 0% | — | 61,000 |
| FAC_C | 0 | 430 | 0 | 0% | — | 92,000 |
| FAC_NE | 1 | 340 | 340 | 100.000% | 0 | 76,000 |
| FAC_SE | 1 | 320 | 290 | 90.625% | 30 | 64,000 |
| FAC_EC | 0 | 380 | 0 | 0% | — | 85,000 |

Selected capacity is 990 units/year for 960 units/year of demand. Weighted network utilization is 96.9697%; the arithmetic average of open-facility utilization is 96.875%; maximum utilization is 100%.

## Shipment decisions

| Origin | Destination | Shipment | Unit cost | Transport cost |
|---|---|---:|---:|---:|
| FAC_NW | ZONE_01 | 60 | 40.48 | 2,428.80 |
| FAC_NW | ZONE_02 | 75 | 32.63 | 2,447.25 |
| FAC_NW | ZONE_03 | 70 | 51.70 | 3,619.00 |
| FAC_NW | ZONE_04 | 65 | 110.34 | 7,172.10 |
| FAC_NW | ZONE_05 | 55 | 155.22 | 8,537.10 |
| FAC_NW | ZONE_07 | 5 | 115.95 | 579.75 |
| FAC_NE | ZONE_07 | 100 | 126.11 | 12,611.00 |
| FAC_NE | ZONE_08 | 80 | 60.72 | 4,857.60 |
| FAC_NE | ZONE_09 | 75 | 32.63 | 2,447.25 |
| FAC_NE | ZONE_10 | 85 | 54.49 | 4,631.65 |
| FAC_SE | ZONE_05 | 30 | 177.85 | 5,335.50 |
| FAC_SE | ZONE_06 | 70 | 125.45 | 8,781.50 |
| FAC_SE | ZONE_11 | 90 | 39.06 | 3,515.40 |
| FAC_SE | ZONE_12 | 100 | 45.25 | 4,525.00 |

ZONE_05 and ZONE_07 are split because FAC_NW and FAC_NE respectively reach binding capacity. Every customer is delivered exactly its demand; all twelve delivery differences are 0.

## Cost breakdown

| Component | Scenario USD/year |
|---|---:|
| TOTAL_FIXED_COST | 214,000.00 |
| TOTAL_TRANSPORT_COST | 71,488.90 |
| TOTAL_OBJECTIVE_COST | 285,488.90 |

The independent recomputation confirms 214,000.00 + 71,488.90 = 285,488.90, with 0 objective difference from the solver value.

## Baseline comparison

The `ALL_FACILITIES_OPEN` baseline is a deliberately defined reference scenario: it opens all six candidates and minimizes shipment cost for that fixed network. It is not an existing company network, current-company state, or industry baseline.

| Metric | Optimized | Baseline |
|---|---:|---:|
| Facilities open | 3 | 6 |
| Network utilization | 96.9697% | 45.7143% |
| Fixed cost | 214,000.00 | 452,000.00 |
| Transport cost | 71,488.90 | 42,015.05 |
| Total scenario cost | 285,488.90 | 494,015.05 |

The optimized result is 208,526.15 lower, a 42.210485% scenario cost reduction relative to the defined baseline. It accepts 29,473.85 more transport cost to avoid 238,000.00 of fixed opening cost. This comparison is not verified financial savings or a real operating outcome.

## Why facilities are selected or rejected

- `FAC_NW` is selected to cover the northwest and west-central demand cluster. Its 330-unit capacity binds. The closest competing three-facility network replaces it with cheaper `FAC_SW`; that saves 13,000 in fixed cost but adds 13,556 in transport cost, so it is 556 more expensive overall.
- `FAC_NE` is selected for the north/east cluster and central overflow. Its 340-unit capacity binds, making the split of ZONE_07 visible.
- `FAC_SE` is selected for the southern/eastern cluster. Its comparatively low 64,000 fixed cost and proximity to ZONE_11 and ZONE_12 offset longer links to ZONE_05 and ZONE_06.
- `FAC_SW` is rejected in the base case because its fixed-cost advantage does not fully compensate for higher transport cost in the best network containing it. It becomes optimal in declared transport-low, fixed-high, and demand-high configurations, confirming that it is a genuine alternative rather than a dominated candidate.
- `FAC_C` offers the largest capacity but has the highest fixed cost. It is not economical at base demand, but enters demand-low and capacity-stress configurations where its capacity and central position matter.
- `FAC_EC` is not selected in any declared base/sensitivity optimum: its 85,000 fixed cost does not provide a sufficient cost/capacity advantage for these inputs. This is a scenario result, not a general claim about east-central facilities.

## Sensitivity and structural changes

Five of the seven non-base scenarios change the network configuration. Demand-low opens `FAC_C` and `FAC_NE`; demand-high adds `FAC_SW` to the base regional pattern; transport-low and fixed-high favor the lower-fixed-cost `FAC_SW`/`FAC_NE`/`FAC_SE` combination; capacity stress changes to `FAC_NW`/`FAC_C`/`FAC_SE`. Transport-high and fixed-low retain the base facilities.

Full scenario results are documented in [sensitivity_analysis.md](sensitivity_analysis.md). A local run generates `tables/sensitivity_results.csv` inside the selected output directory (default `.private_outputs/module_7_25C`).

## Verification results

- Solver-certified optimum: PASS.
- Maximum demand residual: 0.
- Maximum capacity excess: 0.
- Maximum closed-facility flow: 0.
- Minimum shipment: 0.
- Maximum binary-domain distance: 0.
- Objective difference: 0.
- Exhaustive enumeration: 64 subsets, 41 feasible; exact facility and objective agreement.
- Tiny known case: opens A and B, ships 40 on each low-cost local lane, objective 280; manual/Pyomo/enumeration agreement.
- Controlled infeasibility: 2,160 demand vs. 2,100 capacity rejected before solve.

See `reports/validation_summary.md` for the independent Module 7.5C assessment.
