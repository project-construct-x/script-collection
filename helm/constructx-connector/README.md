# Construct-X Connector

![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square)
![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-informational?style=flat-square)

Deploys a Construct-X Connector — an Eclipse Dataspace Components (EDC) runtime
consisting of a **control plane** and a **data plane** — together with a
PostgreSQL database and a HashiCorp Vault instance.
The wallet stores its cryptographic secrets in one of two backends, selected via `vaultInit.mode`:

`hashicorp-dev` — bundled HashiCorp Vault in dev mode (in-memory).

`hashicorp-persistent` — persistent HashiCorp Vault, optionally auto-initialised and unsealed by the chart (non-production).

## Secret storage modes

Secret storage is controlled by the `vaultInit.mode` key.

| Mode                   | Secret storage       | Init / unseal                                 | Survives pod restart |
| ---------------------- | -------------------- | --------------------------------------------- | -------------------- |
| `hashicorp-dev`        | in-memory            | none — fixed dev root token                   | no                   |
| `hashicorp-persistent` | PVC                  | manual, or automatic via `vaultInit.autoInit` | yes                  |


**Rules** (enforced at template rendering time)
- `hashicorp-dev` requires `vault.server.dev.enabled=true`, and
`vault.hashicorp.token` **must equal** `vault.server.dev.devRootToken` —
the runtimes authenticate with the dev root token.
- `hashicorp-persistent` requires `vault.server.dev.enabled=false`.
- `vaultInit.autoInit.enabled=true` is only valid with `hashicorp-persistent`
and requires `vault.server.dataStorage.enabled=true`.
- `autoInit` requires a ServiceAccount with `automountServiceAccountToken=true`
(either `serviceAccount.create=true` + `serviceAccount.automount=true`, or a
pre-created `serviceAccount.name`).
- `vaultInit.aes.enabled=true` is rejected — the connector seeds RSA only.
The `aes` block exists solely to keep the schema uniform across charts.

### Secret seeding

When enabled, the `vault-init` job runs in both modes as a `post-install,post-upgrade` hook
and seeds the data plane token keypair into the Vault:


| Alias value                  | Purpose                       |
| ---------------------------- | ----------------------------- |
| `vaultInit.rsa.privateAlias` | data plane token **signer**   |
| `vaultInit.rsa.publicAlias`  | data plane token **verifier** |


Existing secrets are not overwritten unless `vaultInit.forceRegenerate=true`.

The **DIV client secret** (`iatp.sts.oauth.client.secret_alias`) is *not* seeded
by the chart. It must maually be placed in the Vault under that alias.

### autoInit (persistent mode)

With `vaultInit.autoInit.enabled=true` the job additionally initialises the
Vault (`secret_shares=1`, `secret_threshold=1`), unseals it, enables the KV-v2
mount and a file audit device, and creates a **scoped app token** restricted to the configured KV mount.

Two separate Kubernetes secrets are produced:


| Secret                              | Contents                | Consumed by          |
| ----------------------------------- | ----------------------- | -------------------- |
| `vaultInit.autoInit.keysSecretName` | unseal key + root token | the init job only    |
| `<fullname>-vault-deployment-token` | scoped app token        | control + data plane |


With `autoInit` enabled, `EDC_VAULT_HASHICORP_TOKEN` is injected into both
deployments via `secretKeyRef` instead of being taken from
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

- A Persistent Volume provisioner is required if `postgresql.primary.persistence.enabled: true` and/or `vaultInit.mode=hashicorp-persistent`
- Cluster Internet connection is required when the vault-init job runs (`vaultInit.enabled: true`), so it can pull the required `apk` packages.

## Installation

```bash
# Add dependencies
helm dependency build
# Install
helm install connector . -f my-override-values.yaml
```

## Values

### Top-level

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `install.postgresql` | bool | `true` | Deploy the bundled PostgreSQL instance. |
| `install.vault` | bool | `true` | Deploy the bundled HashiCorp Vault instance. |
| `fullnameOverride` | string | `""` | Overrides the chart fullname used for all resource names. |
| `nameOverride` | string | `""` | Overrides the chart name used in labels. |
| `imagePullSecrets` | list | `[]` | Existing image pull secrets to obtain container images from private registries. |
| `customLabels` | object | `{}` | Add some custom labels. |
| `customCaCerts` | object | `{}` | Custom CA certificates added to the truststore. |

### `participant`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `participant.id` | string | `did:web:changeme` | Participant ID of the connector. |

### `iatp`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `iatp.id` | string | `did:web:changeme` | Decentralized IDentifier (DID) of the connector. |
| `iatp.trustedIssuerId` | string | `change-me` | ID of the trusted issuer used for SI token validation (maps to `EDC_IAM_TRUSTED-ISSUER_EXAMPLE_ID`). |
| `iatp.trustedIssuers` | list | `[]` | Trusted issuers for this runtime. If no `supportedTypes` are specified, the value defaults to `*` for that issuer. |
| `iatp.sts.div.url` | string | `nil` | URL where connectors can request SI tokens. |
| `iatp.sts.oauth.token_url` | string | `https://change-me` | URL where connectors can request OAuth2 access tokens for DIV access. |
| `iatp.sts.oauth.client.id` | string | `change-me` | Client ID for requesting the OAuth2 access token for DIV access. |
| `iatp.sts.oauth.client.secret_alias` | string | `change-me` | Vault alias under which the client secret for DIV access is stored. |
| `iatp.didService.selfRegistration.enabled` | bool | `false` | Whether Service Self Registration is enabled. |
| `iatp.didService.selfRegistration.id` | string | `did:web:changeme` | Unique connector id used for register / unregister service inside the DID document (must be a valid URI). |
| `iatp.cache.enabled` | bool | `true` | Whether the Verifiable Presentation cache is enabled. |
| `iatp.cache.validity` | int | `86400` | Validity of the Verifiable Presentation cache in seconds. |

### `log4j2`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `log4j2.enableJsonLogs` | bool | `true` | Whether to enable the JSON log config in `log4j2.config`. |
| `log4j2.config` | string | _(YAML)_ | Log4j2 configuration for JSON log formatting. |

### `controlplane`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `controlplane.nameOverride` | string | `""` | Overrides the control plane name used in labels. |
| `controlplane.fullnameOverride` | string | `""` | Overrides the control plane fullname used for resource names. |
| `controlplane.hostname` | string | `""` | Hostname where the control plane is reachable. |
| `controlplane.image.repository` | string | `ghcr.io/project-construct-x/con-x-controlplane-postgresql-hashicorp-vault` | Control plane image. When left empty the deployment selects the correct image automatically. |
| `controlplane.image.pullPolicy` | string | `IfNotPresent` | Kubernetes image pull policy. |
| `controlplane.image.tag` | string | `latest` | Image tag. Defaults to `chart.appVersion` if left empty. |
| `controlplane.imagePullSecrets` | list | `[{name: ghcr-creds}]` | ghcr credentials to pull the control plane image. |
| `controlplane.initContainers` | list | `[]` | Additional init containers run before the control plane starts. |
| `controlplane.debug.enabled` | bool | `false` | Enables Java debugging mode. |
| `controlplane.debug.port` | int | `1044` | Port where the debuggee can connect to. |
| `controlplane.debug.suspendOnStart` | bool | `false` | If `true`, the JVM waits until a debugger connects. |
| `controlplane.logs.level` | string | `DEBUG` | Log granularity of the default Console Monitor. |
| `controlplane.bdrs.cache_validity_seconds` | int | `600` | Time a cached BPN/DID resolution map is valid, in seconds. |
| `controlplane.bdrs.server.url` | string | `nil` | URL of the BPN/DID Resolution Service. |
| `controlplane.policy.validation.enabled` | bool | `true` | Enable policy engine validation. |
| `controlplane.podLabels` | object | `{}` | Additional labels for the pod. |
| `controlplane.podAnnotations` | object | `{}` | Additional annotations for the pod. |
| `controlplane.podSecurityContext.seccompProfile.type` | string | `RuntimeDefault` | Restricts the container's syscalls with seccomp. |
| `controlplane.podSecurityContext.runAsUser` | int | `10001` | UID all processes within the pod run as. |
| `controlplane.podSecurityContext.runAsGroup` | int | `10001` | GID all processes within the pod belong to. |
| `controlplane.podSecurityContext.fsGroup` | int | `10001` | GID owning mounted volumes and files created within them. |
| `controlplane.securityContext.capabilities.drop` | list | `[ALL]` | Linux capabilities dropped to reduce the syscall attack surface. |
| `controlplane.securityContext.capabilities.add` | list | `[]` | Linux capabilities added for specialised syscalls. |
| `controlplane.securityContext.readOnlyRootFilesystem` | bool | `true` | Mounts the root filesystem read-only. |
| `controlplane.securityContext.allowPrivilegeEscalation` | bool | `false` | Controls privilege escalation via setuid binaries. |
| `controlplane.securityContext.runAsNonRoot` | bool | `true` | Requires the container to run without root privileges. |
| `controlplane.securityContext.runAsUser` | int | `10001` | UID the container process runs with. |
| `controlplane.env` | object | `nil` | Extra plain environment variables injected into the pod. |
| `controlplane.envValueFrom` | object | `{}` | Extra environment variables sourced from ConfigMaps or Secrets via `valueFrom`. |
| `controlplane.envSecretNames` | list | `[]` | Names of existing Secrets whose keys are mounted as environment variables. |
| `controlplane.envConfigMapNames` | list | `[]` | Names of existing ConfigMaps whose keys are mounted as environment variables. |
| `controlplane.schema.autocreate` | bool | `true` | Database schema auto-creation. |
| `controlplane.volumeMounts` | list | `nil` | Additional volume mounts for the control plane container. |
| `controlplane.volumes` | list | `nil` | Additional volumes for the control plane pod. |
| `controlplane.resources.limits.cpu` | float | `1.5` | Maximum CPU limit. |
| `controlplane.resources.limits.memory` | string | `1024Mi` | Maximum memory limit. |
| `controlplane.resources.requests.cpu` | string | `500m` | Initial CPU request. |
| `controlplane.resources.requests.memory` | string | `1024Mi` | Initial memory request. |
| `controlplane.replicaCount` | int | `1` | Number of control plane pod replicas. |
| `controlplane.autoscaling.enabled` | bool | `false` | Enables Horizontal Pod Autoscaling. |
| `controlplane.autoscaling.minReplicas` | int | `1` | Minimum number of replicas under HPA. |
| `controlplane.autoscaling.maxReplicas` | int | `100` | Maximum number of replicas under HPA. |
| `controlplane.autoscaling.targetCPUUtilizationPercentage` | int | `80` | CPU utilisation target for HPA scale-out. |
| `controlplane.autoscaling.targetMemoryUtilizationPercentage` | int | `80` | Memory utilisation target for HPA scale-out. |
| `controlplane.opentelemetry` | string | _(properties)_ | OpenTelemetry Agent configuration to collect and expose metrics. |
| `controlplane.nodeSelector` | object | `{}` | Node selector constraints for the pod. |
| `controlplane.tolerations` | list | `[]` | Tolerations for the pod. |
| `controlplane.affinity` | object | `{}` | Affinity rules for the pod. |
| `controlplane.url.protocol` | string | `""` | Explicitly declared URL for reaching the DSP API (e.g. if ingresses are not used). |

### `controlplane.endpoints`

Each endpoint creates a Kubernetes Service port and injects the corresponding `WEB_HTTP_*` environment variables into the control plane. Only endpoints listed under an ingress' `endpoints` array are exposed externally.

| Key | Default port | Default path | Description |
|-----|--------------|--------------|-------------|
| `controlplane.endpoints.default` | `9000` | `/api` | Default API for health checks. Must not be added to any ingress. |
| `controlplane.endpoints.management` | `9010` | `/management` | Data management API. Protected by `X-Api-Key`. Must not be internet-facing. |
| `controlplane.endpoints.management.authKey` | — | `password` | Authentication key attached to each request as the `X-Api-Key` header. |
| `controlplane.endpoints.management.jwksUrl` | — | `nil` | If set, the DelegatedAuth service is engaged. |
| `controlplane.endpoints.control` | `9050` | `/control` | Control API for internal control calls. |
| `controlplane.endpoints.protocol` | `9020` | `/dsp` | DSP API for inter-connector communication. Must be internet-facing. |
| `controlplane.endpoints.validation` | `9030` | `/validation` | Validation API. |
| `controlplane.endpoints.metrics` | `9090` | `/metrics` | Metrics API for application metrics. Must not be internet-facing. |

### `controlplane.livenessProbe` / `controlplane.readinessProbe`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `*.enabled` | bool | `true` | Whether the probe is active. |
| `*.initialDelaySeconds` | int | `30` | Seconds before the first probe fires. |
| `*.periodSeconds` | int | `10` | Interval between probes. |
| `*.timeoutSeconds` | int | `5` | Seconds before a probe attempt times out. |
| `*.failureThreshold` | int | `6` | Consecutive failures before the pod is restarted or marked not-ready. |
| `*.successThreshold` | int | `1` | Consecutive successes to transition back to healthy. |

### `controlplane.service`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `controlplane.service.type` | string | `ClusterIP` | Kubernetes Service type. |
| `controlplane.service.labels` | object | `{}` | Additional labels for the service. |
| `controlplane.service.annotations` | object | `{}` | Additional annotations for the service. |

### `controlplane.ingresses`

A list of Ingress definitions. Each entry creates one Ingress resource routing the listed endpoints. The chart ships two pre-configured entries (public and internal). Only entries with `enabled: true` are rendered.

| Key | Type | Description |
|-----|------|-------------|
| `*.enabled` | bool | Render this Ingress resource. |
| `*.hostname` | string | Hostname for all routes in this Ingress. |
| `*.annotations` | object | Annotations added to the Ingress. |
| `*.endpoints` | list | Names of `controlplane.endpoints` keys to expose via this Ingress. |
| `*.className` | string | Ingress class name (e.g. `nginx`, `traefik`). |
| `*.tls.enabled` | bool | Attach a TLS block to this Ingress. |
| `*.tls.secretName` | string | Name of the Secret holding the TLS certificate. |
| `*.certManager.issuer` | string | cert-manager namespace-scoped issuer. |
| `*.certManager.clusterIssuer` | string | cert-manager cluster-scoped issuer. |

### `dataplane`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `dataplane.nameOverride` | string | `""` | Overrides the data plane name used in labels. |
| `dataplane.fullnameOverride` | string | `""` | Overrides the data plane fullname used for resource names. |
| `dataplane.hostname` | string | `""` | Hostname where the data plane is reachable. |
| `dataplane.image.repository` | string | `ghcr.io/project-construct-x/con-x-dataplane-postgresql-hashicorp-vault` | Data plane image. When left empty the deployment selects the correct image automatically. |
| `dataplane.image.pullPolicy` | string | `IfNotPresent` | Kubernetes image pull policy. |
| `dataplane.image.tag` | string | `latest` | Image tag. Defaults to `chart.appVersion` if left empty. |
| `dataplane.imagePullSecrets` | list | `[{name: ghcr-creds}]` | ghcr credentials to pull the data plane image. |
| `dataplane.initContainers` | list | `[]` | Additional init containers run before the data plane starts. |
| `dataplane.debug.enabled` | bool | `false` | Enables Java debugging mode. |
| `dataplane.debug.port` | int | `1044` | Port where the debuggee can connect to. |
| `dataplane.debug.suspendOnStart` | bool | `false` | If `true`, the JVM waits until a debugger connects. |
| `dataplane.logs.level` | string | `DEBUG` | Log granularity of the default Console Monitor. |
| `dataplane.token.refresh.expiry_seconds` | int | `300` | TTL in seconds for access tokens (also known as EDR token). |
| `dataplane.token.refresh.expiry_tolerance_seconds` | int | `10` | Tolerance for token expiry in seconds. |
| `dataplane.token.refresh.refresh_endpoint` | string | `nil` | Optional endpoint for an OAuth2 token refresh. Default is `<PUBLIC_API>/token`. |
| `dataplane.schema.autocreate` | bool | `true` | Database schema auto-creation. |
| `dataplane.aws.endpointOverride` | string | `""` | AWS endpoint override. |
| `dataplane.aws.accessKeyId` | string | `""` | AWS access key ID. |
| `dataplane.aws.secretAccessKey` | string | `""` | AWS secret access key. |
| `dataplane.podLabels` | object | `{}` | Additional labels for the pod. |
| `dataplane.podAnnotations` | object | `{}` | Additional annotations for the pod. |
| `dataplane.podSecurityContext.seccompProfile.type` | string | `RuntimeDefault` | Restricts the container's syscalls with seccomp. |
| `dataplane.podSecurityContext.runAsUser` | int | `10001` | UID all processes within the pod run as. |
| `dataplane.podSecurityContext.runAsGroup` | int | `10001` | GID all processes within the pod belong to. |
| `dataplane.podSecurityContext.fsGroup` | int | `10001` | GID owning mounted volumes and files created within them. |
| `dataplane.securityContext.capabilities.drop` | list | `[ALL]` | Linux capabilities dropped to reduce the syscall attack surface. |
| `dataplane.securityContext.capabilities.add` | list | `[]` | Linux capabilities added for specialised syscalls. |
| `dataplane.securityContext.readOnlyRootFilesystem` | bool | `true` | Mounts the root filesystem read-only. |
| `dataplane.securityContext.allowPrivilegeEscalation` | bool | `false` | Controls privilege escalation via setuid binaries. |
| `dataplane.securityContext.runAsNonRoot` | bool | `true` | Requires the container to run without root privileges. |
| `dataplane.securityContext.runAsUser` | int | `10001` | UID the container process runs with. |
| `dataplane.env` | object | `nil` | Extra plain environment variables injected into the pod. |
| `dataplane.envValueFrom` | object | `{}` | Extra environment variables sourced from ConfigMaps or Secrets via `valueFrom`. |
| `dataplane.envSecretNames` | list | `[]` | Names of existing Secrets whose keys are mounted as environment variables. |
| `dataplane.envConfigMapNames` | list | `[]` | Names of existing ConfigMaps whose keys are mounted as environment variables. |
| `dataplane.volumeMounts` | list | `nil` | Additional volume mounts for the data plane container. |
| `dataplane.volumes` | list | `nil` | Additional volumes for the data plane pod. |
| `dataplane.resources.limits.cpu` | float | `1.5` | Maximum CPU limit. |
| `dataplane.resources.limits.memory` | string | `1024Mi` | Maximum memory limit. |
| `dataplane.resources.requests.cpu` | string | `500m` | Initial CPU request. |
| `dataplane.resources.requests.memory` | string | `1024Mi` | Initial memory request. |
| `dataplane.replicaCount` | int | `1` | Number of data plane pod replicas. |
| `dataplane.autoscaling.enabled` | bool | `false` | Enables Horizontal Pod Autoscaling. |
| `dataplane.autoscaling.minReplicas` | int | `1` | Minimum number of replicas under HPA. |
| `dataplane.autoscaling.maxReplicas` | int | `100` | Maximum number of replicas under HPA. |
| `dataplane.autoscaling.targetCPUUtilizationPercentage` | int | `80` | CPU utilisation target for HPA scale-out. |
| `dataplane.autoscaling.targetMemoryUtilizationPercentage` | int | `80` | Memory utilisation target for HPA scale-out. |
| `dataplane.opentelemetry` | string | _(properties)_ | OpenTelemetry Agent configuration to collect and expose metrics. |
| `dataplane.nodeSelector` | object | `{}` | Node selector constraints for the pod. |
| `dataplane.tolerations` | list | `[]` | Tolerations for the pod. |
| `dataplane.affinity` | object | `{}` | Affinity rules for the pod. |
| `dataplane.url.public` | string | `""` | Explicitly declared URL for reaching the public API (e.g. if ingresses are not used). |

### `dataplane.endpoints`

Each endpoint creates a Kubernetes Service port and injects the corresponding `WEB_HTTP_*` environment variables into the data plane. Only endpoints listed under an ingress' `endpoints` array are exposed externally.

| Key | Default port | Default path | Description |
|-----|--------------|--------------|-------------|
| `dataplane.endpoints.default` | `8181` | `/api` | Default API for health checks. Must not be added to any ingress. |
| `dataplane.endpoints.public` | `9500` | `/public` | Public endpoint where data can be fetched if HttpPull was used. Must be internet-facing. |
| `dataplane.endpoints.control` | `9550` | `/control` | Control API for internal control calls. |
| `dataplane.endpoints.management` | `9510` | `/management` | Data management API. |
| `dataplane.endpoints.proxy` | `9511` | `/proxy` | Proxy API for consumer data transfer. |
| `dataplane.endpoints.proxy.authKey` | — | `password` | Authentication key attached to each request as the `X-Api-Key` header. |
| `dataplane.endpoints.metrics` | `9090` | `/metrics` | Metrics API for application metrics. Must not be internet-facing. |

### `dataplane.livenessProbe` / `dataplane.readinessProbe`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `*.enabled` | bool | `true` | Whether the probe is active. |
| `*.initialDelaySeconds` | int | `30` | Seconds before the first probe fires. |
| `*.periodSeconds` | int | `10` | Interval between probes. |
| `*.timeoutSeconds` | int | `5` | Seconds before a probe attempt times out. |
| `*.failureThreshold` | int | `6` | Consecutive failures before the pod is restarted or marked not-ready. |
| `*.successThreshold` | int | `1` | Consecutive successes to transition back to healthy. |

### `dataplane.service`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `dataplane.service.type` | string | `ClusterIP` | Kubernetes Service type. |
| `dataplane.service.labels` | object | `{}` | Additional labels for the service. |
| `dataplane.service.annotations` | object | `{}` | Additional annotations for the service. |

### `dataplane.ingresses`

A list of Ingress definitions. Each entry creates one Ingress resource routing the listed endpoints. The chart ships two pre-configured entries (public and internal). Only entries with `enabled: true` are rendered.

| Key | Type | Description |
|-----|------|-------------|
| `*.enabled` | bool | Render this Ingress resource. |
| `*.hostname` | string | Hostname for all routes in this Ingress. |
| `*.annotations` | object | Annotations added to the Ingress. |
| `*.endpoints` | list | Names of `dataplane.endpoints` keys to expose via this Ingress. |
| `*.className` | string | Ingress class name (e.g. `nginx`, `traefik`). |
| `*.tls.enabled` | bool | Attach a TLS block to this Ingress. |
| `*.tls.secretName` | string | Name of the Secret holding the TLS certificate. |
| `*.certManager.issuer` | string | cert-manager namespace-scoped issuer. |
| `*.certManager.clusterIssuer` | string | cert-manager cluster-scoped issuer. |

### `postgresql`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `postgresql.jdbcUrl` | string | `jdbc:postgresql://{{ .Release.Name }}-postgresql:5432/edc` | JDBC URL passed to the EDC runtime. |
| `postgresql.auth.database` | string | `edc` | Database name created on first start. Must match the path in `postgresql.jdbcUrl`. |
| `postgresql.auth.username` | string | `user` | Database user the connector connects as. |
| `postgresql.auth.password` | string | `password` | Database password. **Change before production use.** |
| `postgresql.persistence.enabled` | bool | `true` | Persist data across pod restarts. |
| `postgresql.persistence.size` | string | `10Gi` | Size of the allocated Persistent Volume. |
| `postgresql.persistence.storageClass` | string | `""` | Storage Class of the used Storage Provisioner. |
| `postgresql.initdb.scriptsConfigMap` | string | `""` | Optional ConfigMap containing database initialisation scripts. |
| `postgresql.resources.limits.cpu` | string | `500m` | CPU limit for the PostgreSQL container. |
| `postgresql.resources.limits.memory` | string | `1Gi` | Memory limit for the PostgreSQL container. |
| `postgresql.resources.requests.cpu` | string | `250m` | CPU request for the PostgreSQL container. |
| `postgresql.resources.requests.memory` | string | `256Mi` | Memory request for the PostgreSQL container. |

### `vault`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `vault.injector.enabled` | bool | `false` | Vault Agent Injector sidecar. Disabled — the connector reads secrets directly via the Vault HTTP API. |
| `vault.server.dev.enabled` | bool | `true` | Run Vault in dev mode (in-memory, lost on pod restart). **Disable for production** and configure a persistent storage backend instead. |
| `vault.server.dev.devRootToken` | string | `root` | Root token for dev mode. Must match `vault.hashicorp.token`. |
| `vault.server.dataStorage.enabled` | bool | `false` | Persistent Vault data volume for non-dev mode. Enable if `vaultInit.mode=hashicorp-persistent`. |
| `vault.server.dataStorage.size` | string | `1Gi` | Size of the Vault data volume. |
| `vault.server.dataStorage.storageClass` | string | `""` | Storage Class for the Vault data volume. |
| `vault.server.dataStorage.mountPath` | string | `/vault/data` | Mount path for Vault data. Must match `storage "file" { path }` in the standalone config HCL. |
| `vault.server.auditStorage.enabled` | bool | `false` | Persistent audit log volume. Recommended for non-dev mode. Not rotated automatically; blocks Vault when full. |
| `vault.server.auditStorage.size` | string | `1Gi` | Size of the Vault audit volume. |
| `vault.server.auditStorage.storageClass` | string | `""` | Storage Class for the Vault audit volume. |
| `vault.server.auditStorage.mountPath` | string | `/vault/audit` | Mount path for the Vault audit log. |
| `vault.server.standalone.enabled` | bool | `true` | Run Vault in standalone mode. |
| `vault.server.standalone.config` | string | _(HCL)_ | Vault HCL config. `tls_disable = 1` is for cluster-internal use only; `storage "file" { path }` must match `vault.server.dataStorage.mountPath`. |
| `vault.server.postStart` | string | `nil` | Optional post-start script executed inside the Vault container. Can initialise the KV engine or apply policies. Must be set externally. |
| `vault.hashicorp.url` | string | `http://{{ .Release.Name }}-vault:8200` | Vault address reachable from within the cluster. |
| `vault.hashicorp.token` | string | `root` | Vault token used by the connector at runtime. If `vault.server.dev.enabled` is `true`, must match `vault.server.dev.devRootToken`. **Change before production use.** |
| `vault.hashicorp.timeout` | int | `30` | Vault HTTP client timeout in seconds. |
| `vault.hashicorp.healthCheck.enabled` | bool | `true` | Whether the connector checks Vault health on startup. |
| `vault.hashicorp.healthCheck.standbyOk` | bool | `true` | Treat Vault HA standby nodes as healthy. |
| `vault.hashicorp.paths.secret` | string | `/v1/secret` | Mount path for all connector secrets. Must start with /v1/. |
| `vault.hashicorp.paths.health` | string | `/v1/sys/health` | Vault health endpoint polled by the connector and vault-init job. |

### `vaultInit`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `vaultInit.mode` | string | `hashicorp-dev` | Vault initialisation mode: `hashicorp-dev` \| `hashicorp-persistent`. |
| `vaultInit.enabled` | bool | `true` | Whether the vault-init job is rendered. |
| `vaultInit.aes.enabled` | bool | `false` | Request an AES key (wallets). Disabled for the connector. |
| `vaultInit.rsa.enabled` | bool | `true` | Request an RSA keypair (connector). Disabled for the wallets. |
| `vaultInit.rsa.privateAlias` | string | `priv` | Alias of the private key stored in the vault. |
| `vaultInit.rsa.publicAlias` | string | `pub` | Alias of the public key stored in the vault. |
| `vaultInit.forceRegenerate` | bool | `false` | Regenerate secrets even if they already exist. |
| `vaultInit.image.repository` | string | `alpine` | Image repository for the vault-init job. |
| `vaultInit.image.tag` | string | `3.20` | Image tag for the vault-init job. |
| `vaultInit.autoInit.enabled` | bool | `false` | Automatic init/unseal of a persistent Vault. Only for `mode=hashicorp-persistent`. Non-prod only (single unseal key, keys stored as a cluster Secret). |
| `vaultInit.autoInit.keysSecretName` | string | `connector-vault-keys` | Name of the Kubernetes Secret storing the unseal key and root token. |
| `vaultInit.autoInit.auditPath` | string | `/vault/audit/audit.log` | File path for the audit device. Must reside within `vault.server.auditStorage.mountPath`. Leave empty to skip enabling the audit device. |

### `networkPolicy`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `networkPolicy.enabled` | bool | `false` | If `true`, a network policy is created to restrict access to the control and data plane. |
| `networkPolicy.controlplane.from` | list | `[{namespaceSelector: {}}]` | `from` rule for the control plane network policy (defaults to all namespaces). |
| `networkPolicy.dataplane.from` | list | `[{namespaceSelector: {}}]` | `from` rule for the data plane network policy (defaults to all namespaces). |

### `serviceAccount`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `serviceAccount.create` | bool | `true` | Create a dedicated ServiceAccount for the connector and vault-init job. |
| `serviceAccount.automount` | bool | `true` | Automatically mount the ServiceAccount token into pods. |
| `serviceAccount.annotations` | object | `{}` | Annotations added to the ServiceAccount. |
| `serviceAccount.name` | string | `""` | Override the generated ServiceAccount name. |
| `serviceAccount.imagePullSecrets` | list | `[]` | Existing image pull secret bound to the service account for private registries. |

### `tests`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `tests.hookDeletePolicy` | string | `before-hook-creation,hook-succeeded` | Helm test hook delete policy. |

## Sources

- Code: [Construct-X Connector](https://github.com/project-construct-x/constructx-edc)
- Chart: [Tractus-X Connector](https://github.com/eclipse-tractusx/tractusx-edc)
