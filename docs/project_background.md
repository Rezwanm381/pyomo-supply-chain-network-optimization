# Project background

## Purpose

This project demonstrates how a strategic network-design question can be expressed, solved, and independently checked as a mixed-integer linear program (MILP). It is a clean-room portfolio rebuild inspired by graduate optimization coursework and historical Pyomo experimentation. The implementation, scenario data, validation workflow, and public documentation were created for this portfolio case.

The case is intentionally synthetic. It represents no real company, operating network, freight market, or deployment recommendation.

## Why a MILP is appropriate

The decision combines two different mathematical layers:

- **Strategic facility decisions:** opening a candidate facility is an all-or-nothing choice, represented by a binary variable.
- **Shipment-allocation decisions:** annual flow from an open facility to a customer can vary continuously, represented by a nonnegative variable.

Fixed facility costs make the binary layer essential. A continuous-only transportation model could allocate shipments but could not faithfully represent the choice to incur or avoid an indivisible opening cost.

## Capacity and network tradeoffs

Capacity links the two decision layers. Opening fewer facilities avoids fixed cost, but the selected network must still provide enough capacity and may incur higher transport cost. Opening more facilities can shorten shipment lanes but adds fixed cost. The optimum balances those scenario costs while delivering each customer's demand exactly.

The base case contains six binary facility decisions and 72 continuous shipment decisions. It selects `FAC_NW`, `FAC_NE`, and `FAC_SE`, with 990 units/year of selected capacity serving 960 units/year of flow.

## Why optimality is independently checked

A solver's optimal termination is necessary evidence, but a professional workflow should also test the model's inputs, feasibility, decision values, and arithmetic. This project therefore performs independent demand, capacity, domain, and objective checks after the solve.

The small strategic search space also permits exhaustive enumeration: six binary decisions produce \(2^6=64\) possible facility subsets. Forty-one subsets satisfy aggregate capacity. Solving the transportation allocation for each feasible subset identifies the same facilities and objective as the Pyomo MILP. This is a useful independent formulation path for this portfolio-sized case; enumeration grows exponentially and is not presented as a practical method for large industrial networks.

A separate two-facility, two-customer case has a manually derived objective of 280. Pyomo and enumeration both reproduce that value, providing a compact known-answer check.

## Why sensitivity matters

An optimal solution is conditional on its assumptions. The declared sensitivity cases vary demand, transport cost, fixed cost, or capacity and re-solve the complete model. Several cases change the selected network, showing that structural decisions can respond to the economic or capacity environment—not merely change the reported objective.

These patterns are properties of the documented synthetic scenarios. They are not claimed to generalize to actual supply chains.

## Interpretation boundary

All financial outputs are scenario USD/year. The comparison with `ALL_FACILITIES_OPEN` is a scenario cost reduction relative to a deliberately defined reference scenario. It is not verified financial savings, an estimate of company performance, or evidence that the network should be deployed.

