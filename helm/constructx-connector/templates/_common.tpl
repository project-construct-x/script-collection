{{/*
Shared helpers for constructx-connector, wallet and issuer-wallet.
This file must be identical in all three charts except for the helper prefix.
Resolution order in every helper: global.<key> -> local value -> derived default.
Chart specific helpers belong into _helpers.tpl.
Values shared by all charts live directly below global (e.g. global.imagePullSecrets).
Values that differ per chart live below global.<globalKey> (e.g. global.wallet.fullname),
where <globalKey> is defined per chart in _helpers.tpl.
*/}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
global.<globalKey>.fullname -> fullnameOverride -> derived from release and chart name
*/}}
{{- define "conxdc.fullname" -}}
{{- $global := .Values.global | default dict -}}
{{- $override := dig (include "conxdc.globalKey" .) "fullname" (.Values.fullnameOverride | default "") $global -}}
{{- if $override }}
{{- $override | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Defines the Vault URL. Rendered with tpl to allow references like {{ .Release.Name }}.
global.vault.url -> vault.hashicorp.url
*/}}
{{- define "conxdc.vault.url" -}}
{{- $global := .Values.global | default dict -}}
{{- tpl (dig "vault" "url" (.Values.vault.hashicorp.url | default "") $global | required "vault.hashicorp.url or global.vault.url is required") . -}}
{{- end -}}

{{/*
Defines the Vault token used at runtime. Empty if the token is provided by autoInit.
global.vault.token -> vault.hashicorp.token
*/}}
{{- define "conxdc.vault.token" -}}
{{- $global := .Values.global | default dict -}}
{{- dig "vault" "token" (.Values.vault.hashicorp.token | default "") $global -}}
{{- end -}}

{{/*
Defines the vault initialization mode.
global.vault.mode -> vaultInit.mode
*/}}
{{- define "conxdc.vault.mode" -}}
{{- $global := .Values.global | default dict -}}
{{- dig "vault" "mode" (.Values.vaultInit.mode | default "") $global -}}
{{- end -}}

{{/*
Defines if Hashicorp Vault is used (hashicorp-dev | hashicorp-persistent). Returns "true" or "false".
*/}}
{{- define "conxdc.usesHashicorpVault" -}}
{{- has (include "conxdc.vault.mode" .) (list "hashicorp-dev" "hashicorp-persistent") -}}
{{- end -}}

{{/*
Defines if autoInit is enabled. Returns "true" or "false".
Usage: {{- if eq (include "conxdc.vault.autoInit.enabled" .) "true" }}
global.vault.autoInit.enabled -> vaultInit.autoInit.enabled
*/}}
{{- define "conxdc.vault.autoInit.enabled" -}}
{{- $global := .Values.global | default dict -}}
{{- dig "vault" "autoInit" "enabled" (.Values.vaultInit.autoInit.enabled | default false) $global -}}
{{- end -}}

{{/*
Defines the name of the Secret holding unseal key and root token.
Must be identical for all charts sharing one Vault.
global.vault.autoInit.keysSecretName -> vaultInit.autoInit.keysSecretName
*/}}
{{- define "conxdc.vault.autoInit.keysSecretName" -}}
{{- $global := .Values.global | default dict -}}
{{- dig "vault" "autoInit" "keysSecretName" (.Values.vaultInit.autoInit.keysSecretName | default "") $global -}}
{{- end -}}

{{/*
Defines the file path for the audit device. Empty skips enabling the audit device.
global.vault.autoInit.auditPath -> vaultInit.autoInit.auditPath
*/}}
{{- define "conxdc.vault.autoInit.auditPath" -}}
{{- $global := .Values.global | default dict -}}
{{- dig "vault" "autoInit" "auditPath" (.Values.vaultInit.autoInit.auditPath | default "") $global -}}
{{- end -}}

{{/*
Defines the secret path without trailing slash, e.g. "/v1/secret". Single source for the KV mount.
global.vault.secretPath -> vault.hashicorp.paths.secret
*/}}
{{- define "conxdc.vault.secretPath" -}}
{{- $global := .Values.global | default dict -}}
{{- dig "vault" "secretPath" (.Values.vault.hashicorp.paths.secret | default "") $global | trimSuffix "/" -}}
{{- end -}}

{{/*
Defines the KV-v2 mount, derived from the secret path ("/v1/secret" -> "secret").
*/}}
{{- define "conxdc.vault.kvMount" -}}
{{- include "conxdc.vault.secretPath" . | trimPrefix "/v1/" -}}
{{- end -}}

{{/*
Defines if the vault-init job for hashicorp vault does run
*/}}
{{- define "conxdc.vaultInit.jobEnabled" -}}
{{- and .Values.vaultInit.enabled (eq (include "conxdc.usesHashicorpVault" .) "true") -}}
{{- end -}}

{{/*
Defines the image of the vault-init job and the wait-for-app-token init container.
global.vaultInit.image.{repository,tag} -> vaultInit.image.{repository,tag}
*/}}
{{- define "conxdc.vaultInit.image" -}}
{{- $global := .Values.global | default dict -}}
{{- $repository := dig "vaultInit" "image" "repository" (.Values.vaultInit.image.repository | default "alpine") $global -}}
{{- $tag := dig "vaultInit" "image" "tag" (.Values.vaultInit.image.tag | default "3.20") $global -}}
{{- printf "%s:%v" $repository $tag -}}
{{- end -}}

{{/*
Defines Vault Token Secret Name for autoInit
*/}}
{{- define "conxdc.appTokenSecretName" -}}
{{- printf "%s-vault-deployment-token" (include "conxdc.fullname" .) -}}
{{- end -}}

{{/*
Defines the PostgreSQL host.
global.postgresql.host -> postgresql.host -> <release>-postgresql
*/}}
{{- define "conxdc.postgresql.host" -}}
{{- $global := .Values.global | default dict -}}
{{- $local := .Values.postgresql.host | default (printf "%s-postgresql" .Release.Name) -}}
{{- tpl (dig "postgresql" "host" $local $global) . -}}
{{- end -}}

{{/*
Defines the PostgreSQL port.
global.postgresql.port -> postgresql.port -> 5432
*/}}
{{- define "conxdc.postgresql.port" -}}
{{- $global := .Values.global | default dict -}}
{{- dig "postgresql" "port" (.Values.postgresql.port | default 5432) $global -}}
{{- end -}}

{{/*
Defines the JDBC URL.
- global.postgresql.host set: built from host, port and postgresql.auth.database
- postgresql.jdbcUrl set: rendered with tpl (backwards compatible)
- otherwise: built from host, port and postgresql.auth.database
postgresql.jdbcParams (optional) is appended as query string.
*/}}
{{- define "conxdc.postgresql.jdbcUrl" -}}
{{- $global := .Values.global | default dict -}}
{{- if and .Values.postgresql.jdbcUrl (not (dig "postgresql" "host" "" $global)) -}}
{{- tpl .Values.postgresql.jdbcUrl . -}}
{{- else -}}
{{- printf "jdbc:postgresql://%s:%v/%s" (include "conxdc.postgresql.host" .) (include "conxdc.postgresql.port" .) (.Values.postgresql.auth.database | required "postgresql.auth.database is required") -}}
{{- with .Values.postgresql.jdbcParams }}?{{ . }}{{ end -}}
{{- end -}}
{{- end -}}

{{/*
Name of the Secret holding the database credentials (EDC_DATASOURCE_DEFAULT_USER/_PASSWORD).
Consumed by the deployment and, in an umbrella, by the shared PostgreSQL (customUser.existingSecret).
*/}}
{{- define "conxdc.datasourceSecretName" -}}
{{- printf "%s-datasource-credentials" (include "conxdc.fullname" .) -}}
{{- end -}}

{{/*
Defines imagePullSecrets: global + local (+ optional extra list), as {name: ...}, without duplicates.
Renders the complete "imagePullSecrets:" block or nothing.
Usage: {{- include "conxdc.imagePullSecrets" (dict "context" $) | nindent 6 }}
       {{- include "conxdc.imagePullSecrets" (dict "context" $ "extra" .Values.controlplane.imagePullSecrets) | nindent 6 }}
*/}}
{{- define "conxdc.imagePullSecrets" -}}
{{- $global := .context.Values.global | default dict -}}
{{- $all := concat (dig "imagePullSecrets" list $global) (.context.Values.imagePullSecrets | default list) (.extra | default list) -}}
{{- $secrets := list -}}
{{- range $all -}}
{{- if kindIs "string" . -}}
{{- $secrets = append $secrets (dict "name" .) -}}
{{- else -}}
{{- $secrets = append $secrets (dict "name" (get . "name")) -}}
{{- end -}}
{{- end -}}
{{- with ($secrets | uniq) }}
imagePullSecrets:
{{- toYaml . | nindent 2 }}
{{- end -}}
{{- end -}}

{{/*
Defines custom ca certificates: local merged with global. Local wins on equal keys.
Usage: {{- $certs := include "conxdc.customCaCerts" . | fromYaml }}
*/}}
{{- define "conxdc.customCaCerts" -}}
{{- $global := .Values.global | default dict -}}
{{- merge (deepCopy (.Values.customCaCerts | default dict)) (dig "customCaCerts" dict $global) | toYaml -}}
{{- end -}}

{{/*
Defines the ingress class of an ingress entry.
global.ingress.className -> ingresses[].className
Usage inside range: {{ include "conxdc.ingress.className" (dict "context" $ "item" .) }}
*/}}
{{- define "conxdc.ingress.className" -}}
{{- $global := .context.Values.global | default dict -}}
{{- dig "ingress" "className" (.item.className | default "") $global -}}
{{- end -}}

{{/*
Defines the cert-manager cluster issuer of an ingress entry.
global.ingress.clusterIssuer -> ingresses[].certManager.clusterIssuer
*/}}
{{- define "conxdc.ingress.clusterIssuer" -}}
{{- $global := .context.Values.global | default dict -}}
{{- dig "ingress" "clusterIssuer" ((.item.certManager).clusterIssuer | default "") $global -}}
{{- end -}}

{{/*
Defines the annotations of an ingress entry as YAML, including cert-manager annotations.
external-dns follows the resolved host if the annotation is missing or only repeats ingresses[].hostname.
Usage: {{- $annotations := include "conxdc.ingress.annotations" (dict "context" $ "item" . "host" $host) | fromYaml }}
*/}}
{{- define "conxdc.ingress.annotations" -}}
{{- $annotations := deepCopy (.item.annotations | default dict) -}}
{{- $dnsKey := "external-dns.alpha.kubernetes.io/hostname" -}}
{{- if or (not (hasKey $annotations $dnsKey)) (eq (get $annotations $dnsKey | toString) (.item.hostname | default "" | toString)) -}}
{{- $_ := set $annotations $dnsKey .host -}}
{{- end -}}
{{- with (include "conxdc.ingress.clusterIssuer" .) -}}
{{- $_ := set $annotations "cert-manager.io/cluster-issuer" . -}}
{{- end -}}
{{- with (.item.certManager).issuer -}}
{{- $_ := set $annotations "cert-manager.io/issuer" . -}}
{{- end -}}
{{- toYaml $annotations -}}
{{- end -}}
