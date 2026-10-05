{{/*
Validates vaultInit.mode against allowed values and against the matching Vault sub-chart values. 
Call in any rendered template:
  {{- include "wallet.validateVaultInit" (dict "context" . "allowed" (list "hashicorp-dev" "hashicorp-persistent")) -}}
*/}}
{{- define "wallet.validateVaultInit" -}}
{{- $context := .context -}}
{{- $allowed := .allowed -}}
{{- $mode := include "wallet.vault.mode" $context -}}
{{- $autoInit := eq (include "wallet.vault.autoInit.enabled" $context) "true" -}}

{{- /* 0. check if vault.hashicorp.paths.secret starts with /v1/ */ -}}
{{- $secretPath := include "wallet.vault.secretPath" $context -}}
{{- if not (hasPrefix "/v1/" $secretPath) -}}
{{- fail (printf "vault.hashicorp.paths.secret must start with /v1/ followed by a mount name (e.g. /v1/secret), got '%s'" $context.Values.vault.hashicorp.paths.secret) -}}
{{- end -}}

{{- /* 1. check if mode is in allowed list */ -}}
{{- if not (has $mode $allowed) -}}
{{- fail (printf "vaultInit.mode must be one of %v, got '%s'" $allowed $mode) -}}
{{- end -}}

{{- /* 2. check values for inconsistency with given modes */ -}}
{{- if eq $mode "hashicorp-dev" -}}
  {{- if and $context.Values.install.vault (not $context.Values.vault.server.dev.enabled) -}}
  {{- fail "vaultInit.mode=hashicorp-dev requires vault.server.dev.enabled=true" -}}
  {{- end -}}
  {{- if and $context.Values.install.vault (ne (include "wallet.vault.token" $context) $context.Values.vault.server.dev.devRootToken) -}}
  {{- fail "vaultInit.mode=hashicorp-dev requires vault.hashicorp.token to match vault.server.dev.devRootToken" -}}
  {{- end -}}
{{- else if eq $mode "hashicorp-persistent" -}}
  {{- if and $context.Values.install.vault $context.Values.vault.server.dev.enabled -}}
  {{- fail "vaultInit.mode=hashicorp-persistent requires vault.server.dev.enabled=false" -}}
  {{- end -}}
  {{- if and $context.Values.install.vault $autoInit (not $context.Values.vault.server.dataStorage.enabled) -}}
  {{- fail "autoInit with hashicorp-persistent requires vault.server.dataStorage.enabled=true" -}}
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
  {{- end -}}
{{- end -}}

{{- /* 3. check whether persistent mode is set with autoInit */ -}}
{{- if and $autoInit (ne $mode "hashicorp-persistent") -}}
{{- fail "vaultInit.autoInit.enabled=true is only valid with vaultInit.mode=hashicorp-persistent" -}}
{{- end -}}
{{- end -}}