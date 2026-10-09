{{/*
Validates vaultInit.mode against allowed values and against the matching Vault sub-chart values.
Values are read via the helpers in _common.tpl, i.e. global before local.
vault.server.* is only checked if the Vault is installed by this chart (install.vault=true).
Call via the chart specific entrypoint "conxdc.validate" (_helpers.tpl).
*/}}
{{- define "conxdc.validateVaultInit" -}}
{{- $context := .context -}}
{{- $allowed := .allowed -}}
{{- $mode := include "conxdc.vault.mode" $context -}}
{{- $autoInit := eq (include "conxdc.vault.autoInit.enabled" $context) "true" -}}

{{- /* 1. check if mode is in allowed list */ -}}
{{- if not (has $mode $allowed) -}}
  {{- fail (printf "vaultInit.mode must be one of %v, got '%s'" $allowed $mode) -}}
{{- end -}}

{{- /* 2. check values for inconsistency with given modes */ -}}
{{- if eq $mode "hashicorp-dev" -}}
  {{- if and $context.Values.install.vault (not $context.Values.vault.server.dev.enabled) -}}
    {{- fail "vaultInit.mode=hashicorp-dev requires vault.server.dev.enabled=true" -}}
  {{- end -}}
  {{- if and $context.Values.install.vault (ne (include "conxdc.vault.token" $context) (toString $context.Values.vault.server.dev.devRootToken)) -}}
    {{- fail "vaultInit.mode=hashicorp-dev requires vault.hashicorp.token to match vault.server.dev.devRootToken" -}}
  {{- end -}}
{{- else if eq $mode "hashicorp-persistent" -}}
  {{- if and $context.Values.install.vault $context.Values.vault.server.dev.enabled -}}
    {{- fail "vaultInit.mode=hashicorp-persistent requires vault.server.dev.enabled=false" -}}
  {{- end -}}
  {{- if and $context.Values.install.vault $autoInit (not $context.Values.vault.server.dataStorage.enabled) -}}
    {{- fail "autoInit with hashicorp-persistent requires vault.server.dataStorage.enabled=true" -}}
  {{- end -}}
  {{- /* Validate token without autoInit */ -}}
  {{- if and (not $autoInit) (not (include "conxdc.vault.token" $context)) -}}
    {{- fail "vaultInit.mode=hashicorp-persistent without autoInit requires vault.hashicorp.token (or global.vault.token)" -}}
  {{- end -}}
  {{- /* Validate ServiceAccount with enabled autoInit */ -}}
  {{- if $autoInit -}}
    {{- if and (not $context.Values.serviceAccount.create) (not $context.Values.serviceAccount.name) -}}
      {{- fail "vaultInit.autoInit requires either serviceAccount.create=true or a pre-created serviceAccount.name (autoInit needs a ServiceAccount with automountServiceAccountToken=true)" -}}
    {{- end -}}
    {{- /* Validate chart-created SA for automountServiceAccountToken=true */ -}}
    {{- if and $context.Values.serviceAccount.create (not $context.Values.serviceAccount.automount) -}}
      {{- fail "vaultInit.autoInit with serviceAccount.create=true requires serviceAccount.automount=true" -}}
    {{- end -}}
    {{- /* Validate name of the keys Secret, must be shared by all charts using the same Vault */ -}}
    {{- if not (include "conxdc.vault.autoInit.keysSecretName" $context) -}}
      {{- fail "vaultInit.autoInit requires vaultInit.autoInit.keysSecretName (or global.vault.autoInit.keysSecretName)" -}}
    {{- end -}}
  {{- end -}}
{{- end -}}

{{- /* 3. check whether persistent mode is set with autoInit */ -}}
{{- if and $autoInit (ne $mode "hashicorp-persistent") -}}
  {{- fail "vaultInit.autoInit.enabled=true is only valid with vaultInit.mode=hashicorp-persistent" -}}
{{- end -}}

{{- /* 4. check secret path format, the KV mount is derived from it */ -}}
{{- if eq (include "conxdc.usesHashicorpVault" $context) "true" -}}
  {{- $secretPath := include "conxdc.vault.secretPath" $context -}}
  {{- if not (regexMatch "^/v1/[^/]+$" $secretPath) -}}
    {{- fail (printf "vault.hashicorp.paths.secret (or global.vault.secretPath) must have the form /v1/<mount>, got '%s'" $secretPath) -}}
  {{- end -}}
{{- end -}}
{{- end -}}

{{/*
Validates PostgreSQL values.
*/}}
{{- define "conxdc.validatePostgres" -}}
{{- $global := .Values.global | default dict -}}
{{- /* 1. database name is required whenever the JDBC URL is derived */ -}}
{{- if and (not .Values.postgresql.auth.database) (or (not .Values.postgresql.jdbcUrl) (dig "postgresql" "host" "" $global)) -}}
  {{- fail "postgresql.auth.database is required (the JDBC URL is derived from it)" -}}
{{- end -}}
{{- /* 2. credentials are required for a PostgreSQL installed by this chart */ -}}
{{- if and .Values.install.postgresql (not .Values.postgresql.auth.existingSecret) (not .Values.postgresql.auth.password) -}}
  {{- fail "install.postgresql=true requires postgresql.auth.password or postgresql.auth.existingSecret" -}}
{{- end -}}
{{- end -}}
