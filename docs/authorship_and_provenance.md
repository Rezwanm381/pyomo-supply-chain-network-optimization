# Authorship and provenance

## Controlling status

The public-facing project is a new clean-room implementation. Historical Pyomo authorship and submission provenance remain unresolved, so the historical notebook is not presented as solely authored portfolio work and is not part of the future public candidate.

## Historical context

Historical Pyomo material exists as private graduate-course and experimentation context. The surviving evidence supports owner execution of the notebook but does not fully establish original authorship, starter-code lineage, collaborator contributions, or submission status. The historical notebook and workbook remain immutable internal references.

The historical material supplied only the standard conceptual context of facility location and shipment allocation. Its code, names, numerical parameters, saved outputs, and solver structure were not copied into the public implementation.

## Clean-room implementation

The implementation in this repository was independently formulated and implemented for the portfolio. New work includes:

- the Pyomo model and reusable Python module structure;
- the synthetic scenario dataset and deterministic transport-cost construction;
- solver-status handling and independent validation routines;
- facility-subset enumeration and the tiny known-answer case;
- the automated tests, notebooks, figures, reports, and public documentation.

This repository must be described as a clean-room portfolio rebuild inspired by graduate optimization coursework and historical Pyomo experimentation. It must not be represented as the original submitted notebook.

## Scenario-data provenance

Facility and customer identifiers, schematic coordinates, capacities, demands, fixed costs, and the distance-rate assumption are newly defined `SCENARIO_ASSUMPTION` values. Pairwise distances and transport costs are deterministic `DERIVED_SCENARIO_VALUE` fields. No real company, actual lane, sourced freight rate, or public operational dataset is claimed.

## Publication boundary

The Module 8A interim allowlist may include only the new clean-room code, synthetic data, tests, notebooks, reviewed figures, and public documentation. Historical source folders, authorship-review material, internal evidence, local environments, caches, and private archival reports remain outside that boundary; final approval still requires Module 8B.

## Claim controls

Permitted framing:

> Clean-room portfolio rebuild inspired by graduate optimization coursework and historical Pyomo experimentation.

Prohibited framing includes claims that the historical notebook was solely authored or submitted by the owner, that this code is the historical submission, that the scenario describes a real company, or that its comparison represents deployed or realized financial savings.
