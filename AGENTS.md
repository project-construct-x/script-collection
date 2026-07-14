# AGENTS.md

Construct-X `script-collection`: deploy/config artifacts for running Construct-X data space
components. Remote: `project-construct-x/script-collection`, default branch `main`.

## Layout & naming conventions (follow these exactly)
- Organized by **artifact type** at top level: `docker/`, `helm/`, `bruno/`, `configurator/`.
- Scenario folders use consistent names across artifact types, with **no** `construct-x`/`con-x`
  prefix (the org is implied):
  - `single-node` = one Connector + one Wallet (minimal). Lives in `docker/single-node`,
    `helm/single-node`.
  - `local-testbed` = two Connectors + wallets + shared Postgres/Vault, end-to-end. Lives in
    `docker/local-testbed`, `bruno/local-testbed`.
- Each Docker scenario is self-contained (its own `docker-compose.yaml` + `additional_config/`).
- `helm/single-node` is an **umbrella** chart depending on upstream component charts.
- `configurator/` = Python script that starts and configures a node, replacing the
  manual Bruno onboarding flow.

## Conventions
- Add an Apache-2.0 SPDX license header to new source files (see existing headers in the testbed
  `docker-compose.yaml`). Code is Apache-2.0; non-code is CC-BY-4.0 (`LICENSE_non-code`).
- PRs target `main`; use Conventional Commits and link an issue (`CONTRIBUTING.md`).
