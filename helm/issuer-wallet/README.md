# Construct-X Issuer-Wallet

![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square)
![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-informational?style=flat-square)

Deploys the [Construct-X Wallet](https://github.com/project-construct-x/wallet) — an EDC IdentityHub runtime — together with a PostgreSQL database and configures it to act as an dataspace issuer. 
The wallet stores its cryptographic secrets in one of three backends, selected via `vaultInit.mode`:

`hashicorp-dev` — bundled HashiCorp Vault in dev mode (in-memory).

`hashicorp-persistent` — persistent HashiCorp Vault, optionally auto-initialised and unsealed by the chart (non-production).

`postgres` — secrets kept in the PostgreSQL-backed SQL vault (see [SqlVaultExtension](https://github.com/project-construct-x/wallet/blob/develop/extensions/con-x/sql-vault/README.md#sqlvaultextension)). Requires no HashiCorp Vault.

## Secret storage modes

Secret storage is controlled by the `vaultInit.mode` key.
The chart derives the container image and all backend-specific resources from it.

| Mode                   | Secret storage       | Init / unseal                                 | Survives pod restart |
| ---------------------- | -------------------- | --------------------------------------------- | -------------------- |
| `hashicorp-dev`        | in-memory            | none — fixed dev root token                   | no                   |
| `hashicorp-persistent` | PVC                  | manual, or automatic via `vaultInit.autoInit` | yes                  |
| `postgres`             | Secret               | automatic via `vaultInit.enabled`             | yes                  |

**Rules** (enforced at template rendering time)
- `hashicorp-dev` requires `vault.server.dev.enabled=true`, and
`vault.hashicorp.token` **must equal** `vault.server.dev.devRootToken` —
the runtimes authenticate with the dev root token.
- `hashicorp-persistent` requires `vault.server.dev.enabled: false`.
- `vaultInit.autoInit.enabled: true` is valid only with `hashicorp-persistent` and
  requires `vault.server.dataStorage.enabled: true`.
- `autoInit` requires a ServiceAccount with `automountServiceAccountToken=true`
(either `serviceAccount.create=true` + `serviceAccount.automount=true`, or a
pre-created `serviceAccount.name`).
- `postgres` requires `install.vault: false`.
- `vaultInit.rsa.enabled=true` is rejected — the wallet seeds AES only.
The `rsa` block exists solely to keep the schema uniform across charts..

### Secret seeding

The `vault-init` job runs in both modes as a `post-install,post-upgrade` hook
and seeds the wallet token key into the Vault:


| Alias value                  | Purpose                       |
| ---------------------------- | ----------------------------- |
| `vaultInit.aes.alias`        | wallet token key              |


Existing secrets are not overwritten unless `vaultInit.forceRegenerate=true`.

### autoInit (persistent mode)

With `vaultInit.autoInit.enabled=true` the job additionally initialises the
Vault (`secret_shares=1`, `secret_threshold=1`), unseals it, enables the KV-v2
mount and a file audit device, and creates a **scoped app token** restricted to the configured KV mount.

Two separate Kubernetes secrets are produced:


| Secret                              | Contents                | Consumed by          |
| ----------------------------------- | ----------------------- | -------------------- |
| `vaultInit.autoInit.keysSecretName` | unseal key + root token | the init job only    |
| `<fullname>-vault-deployment-token` | scoped app token        | wallet               |


With `autoInit` enabled, `EDC_VAULT_HASHICORP_TOKEN` is injected into the wallet
deployment via `secretKeyRef` instead of being taken from
`vault.hashicorp.token`.

> **autoInit is not production safe.** A single unseal key and the root token
> are stored as a Kubernetes secret in the release namespace. The Vault is
> sealed again after a pod restart and is *not* unsealed automatically. For
> production use KMS auto-unseal and external key management, and keep
> `autoInit.enabled=false`.

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Kubernetes  | 1.29+   |
| Helm        | 3.14+   |

- A Persistent Volume provisioner is required if `postgresql.primary.persistence.enabled: true`
- Cluster Internet connection is required when the vault-init job runs (`vaultInit.enabled: true` with `vaultInit.mode = hashicorp-dev` or
`hashicorp-persistent`), so it can pull the required `apk` packages.

## Installation

```bash
# Add Hashicorp Repository
helm repo add hashicorp https://helm.releases.hashicorp.com
# Add dependencies
helm dependency build
# Install
helm install issuer . -f my-override-values.yaml
```

## Values

### Top-level

| Key | Type | Default | Description |
|---|---|---|---|
| `install.postgresql` | bool | `true` | Install the bundled PostgreSQL sub-chart. Set to `false` to use an external database. |
| `install.vault` | bool | `true` | Install the bundled Vault sub-chart. Set to `false` to use an external Vault. |
| `fullnameOverride` | string | `"issuer"` | Overrides the chart fullname used for all resource names. |
| `nameOverride` | string | `"issuer"` | Overrides the chart name used in labels. |
| `imagePullSecrets` | list | `[]` | Pull secrets for private image registries. |
| `customCaCerts` | object | `{}` | Custom CA certificates added to the Java truststore at startup. |

### `wallet`

| Key | Type | Default | Description |
|---|---|---|---|
| `wallet.image.repositoryVaultWallet` | string | `ghcr.io/project-construct-x/wallet`             | `vaultInit.mode` = `hashicorp-dev` / `hashicorp-persistent`.                                                |
| `wallet.image.repositoryPsqlWallet`  | string | `ghcr.io/project-construct-x/wallet-sql-vault`   | Container image used when `vaultInit.mode` = `postgres` . |
| `wallet.image.tag` | string | `0.18.0-1` | Image tag. Defaults to `chart.appVersion` if left empty. |
| `wallet.image.pullPolicy` | string | `IfNotPresent` | Kubernetes image pull policy. |
| `wallet.initContainers` | list | `[]` | Additional init containers run before the wallet starts. |
| `wallet.podLabels` | object | `{}` | Extra labels applied to the wallet pod. |
| `wallet.podAnnotations` | object | `{}` | Extra annotations applied to the wallet pod. |
| `wallet.useSVE` | bool | `false` | Disables SVE CPU instructions via `JAVA_TOOL_OPTIONS`. Enable on SVE-capable nodes if the JVM crashes with illegal instruction errors. |
| `wallet.debug.enabled` | bool | `false` | Enables the JDWP remote debug socket. Never use in production. |
| `wallet.debug.port` | int | `1044` | JDWP listen port inside the container. |
| `wallet.debug.suspendOnStart` | bool | `false` | If `true`, the JVM suspends until a debugger connects. |
| `wallet.hostname` | string | `issuer.staging.construct-x.net` | Public hostname. Used in `did:web` URLs and ingress routing. |
| `wallet.superuser.createSecret` | bool | `true` | Creates a Kubernetes Secret from the values below and mounts it via `envFrom`. Set to `false` and reference an external secret via `envSecretNames` instead. |
| `wallet.superuser.id` | string | `admin` | Participant context ID of the super-user. |
| `wallet.superuser.apiKey` | string | `YWRtaW4.adminKey` | API key for the super-user. Format: `base64(<id>).<random-suffix>`. **Change before production use.** |
| `wallet.superuser.publicKeyAlias` | string | `admin#pubkey` | Vault alias for the super-user RSA public key. Generated by the wallet on first start. |
| `wallet.superuser.privateKeyAlias` | string | `admin#privkey` | Vault alias for the super-user RSA private key. Generated by the wallet on first start. |
| `wallet.didweb.https` | bool | `true` | Use `https://` in `did:web` URLs. Set to `false` only for local testing. |
| `wallet.issuer.statuslist.callbackAddress`| string | `https://{ wallet.ingresses[0].hostname }{ wallet.endpoints.statuslist.path }` | Callback address for statuslist. |
| `wallet.env` | object | `{}` | Extra plain environment variables injected into the wallet pod. |
| `wallet.envValueFrom` | object | `{}` | Extra environment variables sourced from ConfigMaps or Secrets via `valueFrom`. |
| `wallet.envSecretNames` | list | `[]` | Names of existing Secrets whose keys are mounted as environment variables via `envFrom`. |
| `wallet.envConfigMapNames` | list | `[]` | Names of existing ConfigMaps whose keys are mounted as environment variables via `envFrom`. |
| `wallet.replicaCount` | int | `1` | Number of wallet pod replicas. |
| `wallet.resources.limits.cpu` | string | `500m` | CPU limit for the wallet container. |
| `wallet.resources.limits.memory` | string | `512Mi` | Memory limit for the wallet container. |
| `wallet.resources.requests.cpu` | string | `250m` | CPU request for the wallet container. |
| `wallet.resources.requests.memory` | string | `128Mi` | Memory request for the wallet container. |
| `wallet.autoscaling.enabled` | bool | `false` | Enables Horizontal Pod Autoscaling. |
| `wallet.autoscaling.minReplicas` | int | `1` | Minimum number of replicas under HPA. |
| `wallet.autoscaling.maxReplicas` | int | `100` | Maximum number of replicas under HPA. |
| `wallet.autoscaling.targetCPUUtilizationPercentage` | int | `80` | CPU utilisation target for HPA scale-out. |
| `wallet.autoscaling.targetMemoryUtilizationPercentage` | int | `80` | Memory utilisation target for HPA scale-out. |
| `wallet.nodeSelector` | object | `{}` | Node selector constraints for the wallet pod. |
| `wallet.tolerations` | list | `[]` | Tolerations for the wallet pod. |
| `wallet.affinity` | object | `{}` | Affinity rules for the wallet pod. |
| `wallet.volumeMounts` | list | `[]` | Additional volume mounts for the wallet container. |
| `wallet.volumes` | list | `[]` | Additional volumes for the wallet pod. |

### `wallet.endpoints`

Each endpoint creates a Kubernetes Service port and injects the corresponding `WEB_HTTP_*` environment variables into the issuer-wallet. Only endpoints listed under an ingress' `endpoints` array are exposed externally.

| Key | Default port | Default path | Description |
|---|---|---|---|
| `wallet.endpoints.default` | `8181` | `/api` | Observability endpoint (health checks). Must not be added to public ingresses. |
| `wallet.endpoints.identity` | `15151` | `/api/identity` | Management API. Protected by `X-Api-Key`. Must not be internet-facing. |
| `wallet.endpoints.identity.authKeyAlias` | `sup3r$3cr3t` | — | Vault alias whose stored value is validated against the `X-Api-Key` request header. |
| `wallet.endpoints.issueradmin` | `15152` | `/api/issuer` | Issuer Admin API endpoint, must not be internet facing. |
| `wallet.endpoints.did` | `80` | `/` | DID document service. Resolves `did:web` documents. Must be publicly reachable. |
| `wallet.endpoints.sts` | `9292` | `/api/sts` | Secure Token Service. Issues self-signed ID tokens for DCP flows. Public-facing. |
| `wallet.endpoints.statuslist` | `9999` | `/statuslist` | StatusList API, used to check the status of verifiable credentials. Public-facing. |
| `wallet.endpoints.issuance` | `13132` | `/api/issuance` | DCP Issuance API. Public-facing. |

### `wallet.livenessProbe` / `wallet.readinessProbe`

Both probes call `GET <default.path>/check/liveness` and `GET <default.path>/check/readiness` on the `default` endpoint port.

| Key | Type | Default | Description |
|---|---|---|---|
| `*.enabled` | bool | `true` | Whether the probe is active. |
| `*.initialDelaySeconds` | int | `5` | Seconds before the first probe fires. Increase to 30+ on slow cold starts. |
| `*.periodSeconds` | int | `5` | Interval between probes. |
| `*.timeoutSeconds` | int | `5` | Seconds before a probe attempt times out. |
| `*.failureThreshold` | int | `6` | Consecutive failures before the pod is restarted or marked not-ready. |
| `*.successThreshold` | int | `1` | Consecutive successes to transition back to healthy. |

### `wallet.service`

| Key | Type | Default | Description |
|---|---|---|---|
| `wallet.service.type` | string | `ClusterIP` | Kubernetes Service type. `ClusterIP` is recommended when an ingress or gateway is used. |
| `wallet.service.annotations` | object | `{}` | Annotations added to the Service resource. |

### `wallet.ingresses`

A list of Ingress definitions. Each entry creates one Ingress resource routing the listed endpoints. The chart ships two pre-configured entries (public and internal). Only entries with `enabled: true` are rendered.

| Key | Type | Description |
|---|---|---|
| `*.enabled` | bool | Render this Ingress resource. |
| `*.hostname` | string | Hostname for all routes in this Ingress. |
| `*.annotations` | object | Annotations added to the Ingress (e.g. cert-manager, external-dns). |
| `*.endpoints` | list | Names of `wallet.endpoints` keys to expose via this Ingress. |
| `*.className` | string | Ingress class name (e.g. `nginx`, `traefik`). |
| `*.tls.enabled` | bool | Attach a TLS block to this Ingress. |
| `*.tls.secretName` | string | Name of the Secret holding the TLS certificate. |
| `*.certManager.issuer` | string | cert-manager namespace-scoped issuer. |
| `*.certManager.clusterIssuer` | string | cert-manager cluster-scoped issuer. |

### `serviceAccount`

| Key | Type | Default | Description |
|---|---|---|---|
| `serviceAccount.create` | bool | `true` | Create a dedicated ServiceAccount for the issuer-wallet and vault-init job. |
| `serviceAccount.automount` | bool | `true` | Automatically mount the ServiceAccount token into pods. |
| `serviceAccount.annotations` | object | `{}` | Annotations added to the ServiceAccount (e.g. for Vault Kubernetes auth). |
| `serviceAccount.name` | string | `""` | Override the generated ServiceAccount name. |

### `postgresql`

The chart uses the Cloudpirates PostgreSQL Chart.

| Key | Type | Default | Description |
|---|---|---|---|
| `postgresql.jdbcUrl` | string | `jdbc:postgresql://issuer-postgresql:5432/wallet` | JDBC URL passed to the issuer-wallet. |
| `postgresql.auth.database` | string | `issuer` | Database name created on first start. |
| `postgresql.auth.username` | string | `user` | Database user the issuer-wallet connects as. |
| `postgresql.auth.password` | string | `password` | Database password. **Change before production use.** |
| `postgresql.persistence.enabled` | bool | `true` | Persist primary node data. Disable only for throwaway test environments. |
| `postgresql.persistence.size` | string | `10Gi` | Size of allocated Persistent Volume. |
| `postgresql.persistence.storageClass` | string | `""` | Storage Class of used Storage Provisioner. |
| `postgresql.initdb.scriptsConfigMap` | string | `""` | Name of ConfigMap for Database Initialization. |

### `vault`

| Key | Type | Default | Description |
|---|---|---|---|
| `vault.injector.enabled` | bool | `false` | Vault Agent Injector sidecar. Disabled — the issuer-wallet reads secrets directly via the Vault HTTP API. |
| `vault.server.dev.enabled` | bool | `true` | Run Vault in dev mode (in-memory, no persistence). **Disable for production.** |
| `vault.server.dev.devRootToken` | string | `root` | Root token for dev mode. Must match `vault.hashicorp.token`. |
| `vault.server.dataStorage.enabled`  |	bool  |	`false` |	Persist Vault data. Required for `hashicorp-persistent` + `autoInit`. |
| `vault.server.dataStorage.size` |	string  |	`1Gi`  |	Size of the Vault data PVC. |
| `vault.server.dataStorage.storageClass`	| string	| `""`	| Storage class for the Vault data PVC. Empty = cluster default provisioner.| 
| `vault.server.dataStorage.mountPath`  |	string  |	`/vault/data` |	Must match storage "file" { path } in the standalone config. |
| `vault.server.auditStorage.enabled` |	bool  |	`false` |	Persist the Vault audit log (not rotated automatically).  |
| `vault.server.auditStorage.size`	| string	| `1Gi`	| Size of the Vault audit PVC.| 
| `vault.server.auditStorage.storageClass`	| string	| `""`	| Storage class for the audit PVC. Empty = cluster default provisioner.| 
| `vault.server.auditStorage.mountPath` |	string  |	`/vault/audit`  |	Audit log volume mount path.  |
| `vault.server.standalone.enabled` |	bool  |	`true` |	Enable standalone (persistent) Vault. Ignored when dev.enabled: true. |
| `vault.server.standalone.config`	| string	| (chart default)	| Vault server HCL config (listener, storage backend, ui). The `storage "file" { path }` must match `dataStorage.mountPath`.| 
| `vault.server.postStart` | string | `nil` | Optional post-start script executed inside the Vault container. Must be set externally. |
| `vault.hashicorp.url` | string | `http://issuer-vault:8200` | Vault address reachable from within the cluster. |
| `vault.hashicorp.token` | string | `root` | Vault token used by the issuer-wallet at runtime. **Change before production use.** |
| `vault.hashicorp.timeout` | int | `30` | Vault HTTP client timeout in seconds. |
| `vault.hashicorp.healthCheck.enabled` | bool | `true` | Whether the issuer-wallet checks Vault health on startup. |
| `vault.hashicorp.healthCheck.standbyOk` | bool | `true` | Treat Vault HA standby nodes as healthy. |
| `vault.hashicorp.paths.secret` | string | `/v1/secret` | Mount path for all issuer-wallet secrets. Must start with /v1/. |
| `vault.hashicorp.paths.health` | string | `/v1/sys/health` | Vault health endpoint polled by the issuer-wallet and vault-init job. |

### `vaultInit`

| Key | Type | Default | Description |
|---|---|---|---|
| `vaultInit.mode` | string | `hashicorp-dev` | Secret backend. One of `hashicorp-dev`, `hashicorp-persistent`, `postgres`. |
| `vaultInit.enabled` | bool | `true` | Whether the vault-init job / sql-aes secret is rendered. |
| `vaultInit.aes.enabled` | bool | `true` | Generate an AES-256 key (wallets). |
| `vaultInit.aes.alias` | string | `issuer-wallet-aes-key-alias` | AES key alias. In `postgres` mode also the mounted file name. |
| `vaultInit.rsa.enabled` | bool | `false` | Generate an RSA keypair (connector only; disabled here). |
| `vaultInit.rsa.privateAlias` | string | `priv` | Vault alias of the RSA private key. |
| `vaultInit.rsa.publicAlias` | string | `pub` | Vault alias of the RSA public key. |
| `vaultInit.forceRegenerate` | bool | `false` | Regenerate secrets even if present (hashicorp modes only). |
| `vaultInit.image.repository` | string | `alpine` | Image of the vault-init job. |
| `vaultInit.image.tag` | string | `3.20` | Tag of the vault-init job image. |
| `vaultInit.autoInit.enabled` | bool | `false` | Auto-initialise and unseal a persistent Vault. `hashicorp-persistent` only. Non-production. |
| `vaultInit.autoInit.keysSecretName` | string | `issuer-vault-keys` | Secret holding the unseal key and root token. |
| `vaultInit.autoInit.auditPath` | string | `/vault/audit/audit.log` | File audit device path. Empty to skip enabling audit. |

## Sources

- Code: [Construct-X Wallet](https://github.com/project-construct-x/wallet)
- Chart: [Tractus-X IdentityHub](https://github.com/eclipse-tractusx/tractusx-identityhub)