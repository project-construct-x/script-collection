# Construct-X Script Collection

A collection of scripts to easily configure and run Construct-X data space components with Docker
or Kubernetes.

## About
The Construct-X data space requires participants to use various components (like a Connector, a
wallet, etc.), located in different repositories in the [Construct-X GitHub Organization](https://github.com/project-construct-x/).
While these components work together and can be deployed and configured differently, this repository
aims to collect different Docker and Docker Compose files, Kubernetes configurations and Helm charts,
as well as automatic configuration scripts to help participants get onboarded.

## Repository Structure
The repository is organized by artifact type. Each folder contains its own `README.md` with more
details.

```
.
├── docker/                 # Docker Compose deployments
│   ├── single-node/        # One Connector + one Wallet (minimal setup)
│   └── local-testbed/      # Two Connectors + wallets for end-to-end testing
├── helm/                   # Kubernetes Helm charts
│   └── single-node/        # Umbrella chart: one Connector + one Wallet
├── bruno/                  # Bruno HTTP collections
│   └── local-testbed/      # Collection for the local testbed
└── configurator/           # Python script to start & configure a node
```

## Documentation
This documentation is located in different READMEs in the dedicated folders.

## License
All code files are distributed under the Apache 2.0 license. See [LICENSE](./LICENSE) for more information.

All non-code files are distributed under the Creative Commons Attribution 4.0 International license. See [LICENSE_non-code](./LICENSE_non-code) for more information.
