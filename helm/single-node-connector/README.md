# Single Node Connector

![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square)
![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-informational?style=flat-square)

Umbrella chart that deploys a Construct-X connector (control plane + data plane) and a wallet
for one participant, sharing one HashiCorp Vault and one PostgreSQL instance.

- Connector: [Code](https://github.com/project-construct-x/constructx-edc) / [Chart](https://github.com/project-construct-x/script-collection/tree/main/helm/constructx-connector)
- Wallet: [Code](https://github.com/project-construct-x/wallet) / [Chart](https://github.com/project-construct-x/script-collection/tree/main/helm/wallet)

The connector chart provides Vault and PostgreSQL, the wallet uses them. Shared settings are defined once under `global.*` and read by both
subcharts. Connector and Wallet store their cryptographic secrets in one of two backends, selected via `global.vault.mode`:

`hashicorp-dev` — bundled HashiCorp Vault in dev mode (in-memory).

`hashicorp-persistent` — persistent HashiCorp Vault, optionally auto-initialised and unsealed by the chart (non-production).

## Secret storage modes

Secret storage is controlled by the `global.vault.mode` key.

| Mode                   | Secret storage       | Init / unseal                                    | Survives pod restart |
| ---------------------- | -------------------- | ------------------------------------------------ | -------------------- |
| `hashicorp-dev`        | in-memory            | none — fixed dev root token                      | no                   |
| `hashicorp-persistent` | PVC                  | manual, or automatic via `global.vault.autoInit` | yes                  |

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Kubernetes  | 1.29+   |
| Helm        | 3.14+   |

- A Persistent Volume provisioner is required
- Cluster Internet connection is required, so the vault-init job can pull the required `apk` packages.

## Installation

Install with `--render-subchart-notes`. The umbrella notes only show the shared overview. Endpoints, credentials
and warnings come from the subchart notes.

```bash
helm install edc . -f /my-override-values.yaml --render-subchart-notes
```

> **`global.vault.autoInit` is not production safe.** A single unseal key and the root token
> are stored as a Kubernetes secret in the release namespace. The Vault is
> sealed again after a pod restart and is *not* unsealed automatically. For
> production use KMS auto-unseal and external key management, and keep
> `global.vault.autoInit.enabled=false`.

## Configuration

### Global values

Shared by connector and wallet. See the "global" sections of the
[connector](https://github.com/project-construct-x/script-collection/tree/main/helm/constructx-connector/README.md) and [wallet](https://github.com/project-construct-x/script-collection/tree/main/helm/wallet/README.md) READMEs for the local
fallbacks.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `global.participant.did` | string | `"did:web:wallet.staging.construct-x.net:user"` | DID of the participant. Must resolve via the wallet hostname. Used as participant ID, issuer ID and STS client ID. |
| `global.connector.fullname` | string | `"edc"` | Fullname of the connector. Base of all connector resource and service names. |
| `global.connector.controlplane.hostname` | string | `"controlplane.staging.construct-x.net"` | Public hostname of the control plane. Used by all `controlplane.ingresses` without own hostname. |
| `global.connector.dataplane.hostname` | string | `"dataplane.staging.construct-x.net"` | Public hostname of the data plane. Used by all `dataplane.ingresses` without own hostname. |
| `global.wallet.fullname` | string | `"wallet"` | Fullname of the wallet. Must differ from the connector fullname. |
| `global.wallet.hostname` | string | `"wallet.staging.construct-x.net"` | Public hostname of the wallet. Used by all `wallet.ingresses` without own hostname. |
| `global.vault.url` | string | `"http://{{ .Release.Name }}-vault:8200"` | URL of the shared Vault. |
| `global.vault.token` | string | `"root"` | Vault token. Dev mode: must match `constructx-connector.vault.server.dev.devRootToken`. Not needed with autoInit. |
| `global.vault.secretPath` | string | `"/v1/secret"` | KV v2 path used by all apps and both vault-init jobs. The KV mount is derived from it. |
| `global.vault.mode` | string | `"hashicorp-dev"` | `hashicorp-dev` or `hashicorp-persistent` |
| `global.vault.autoInit.enabled` | bool | `false` | Initialise and unseal a persistent Vault automatically. Only for `hashicorp-persistent`, non-production only. |
| `global.vault.autoInit.keysSecretName` | string | `"constructx-vault-keys"` | Secret holding the unseal key and root token. Shared by both vault-init jobs. |
| `global.postgresql.host` | string | `"{{ .Release.Name }}-postgresql"` | Host of the shared PostgreSQL |
| `global.postgresql.port` | int | `5432` | Port of the shared PostgreSQL |
| `global.ingress.className` | string | `"nginx"` | Ingress class of all ingresses without own `className` |
| `global.ingress.clusterIssuer` | string | `"letsencrypt-staging"` | cert-manager ClusterIssuer of all ingresses without own issuer |
| `global.imagePullSecrets` | list | `[]` | Image pull secrets of all pods, merged with the local lists |

### Subchart values

All other values are set below the subchart key and documented in the subchart READMEs:

- `constructx-connector.*`: [constructx-connector](https://github.com/project-construct-x/script-collection/tree/main/helm/constructx-connector/README.md), including `vault.*` and `postgresql.*` of the shared instances
- `wallet.*`: [wallet](https://github.com/project-construct-x/script-collection/tree/main/helm/wallet/README.md)

### Coupling set by this chart

The following values in `values.yaml` connect the two subcharts. Change them only together:

| Value | Purpose |
|-------|---------|
| `constructx-connector.install.vault/postgresql: true`, `wallet.install.vault/postgresql: false` | The connector provides the shared instances |
| `constructx-connector.postgresql.customUser.*` | Creates the wallet database and user from the wallet datasource Secret |
| `wallet.postgresql.auth.database` | Must match `customUser.database` |
| `constructx-connector.vaultInit.rsa.*Alias`, `wallet.vaultInit.aes.alias` | Must not collide in the shared secret path |

### STS token URL

Connector and wallet run in the same namespace, so the connector can request STS tokens cluster-internally:
```yaml
constructx-connector:
  iatp:
    sts:
      oauth:
        token_url: "http://<wallet-fullname>:9292/api/sts/token"
```
