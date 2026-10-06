{{/*
Expand the name of the chart.
*/}}
{{- define "issuer-wallet.name" -}}
{{- default .Chart.Name .Values.nameOverride | replace "+" "_"  | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name. Overrides local fullname values with globals, if set.
*/}}
{{- define "issuer-wallet.fullname" -}}
{{- $global := .Values.global | default dict -}}
{{- $override := dig "wallet" "fullname" .Values.fullnameOverride $global -}}
{{- if $override -}}
{{- tpl $override . | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "issuer-wallet.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Control Common labels
*/}}
{{- define "issuer-wallet.labels" -}}
helm.sh/chart: {{ include "issuer-wallet.chart" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Control Common Server labels
*/}}
{{- define "issuer-wallet.server.labels" -}}
helm.sh/chart: {{ include "issuer-wallet.chart" . }}
{{ include "issuer-wallet.server.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: wallet-server
app.kubernetes.io/part-of: wallet
{{- end }}

{{/*
Control Selector labels
*/}}
{{- define "issuer-wallet.server.selectorLabels" -}}
app.kubernetes.io/name: {{ include "issuer-wallet.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "issuer-wallet.server.serviceaccount.name" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "issuer-wallet.fullname" . ) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "issuer-wallet.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "issuer-wallet.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Defines Image depending on chosen Vault Mode
*/}}
{{- define "issuer-wallet.image" -}}
{{- $tag := .Values.wallet.image.tag | default .Chart.AppVersion -}}
{{- if eq .Values.vaultInit.mode "postgres" -}}
{{- printf "%s:%s" .Values.wallet.image.repositoryPsqlWallet $tag -}}
{{- else -}}
{{- printf "%s:%s" .Values.wallet.image.repositoryVaultWallet $tag -}}
{{- end -}}
{{- end -}}

{{/*
Defines AES-Key-Alias
*/}}
{{- define "issuer-wallet.aesKeyAlias" -}}
{{- .Values.vaultInit.aes.alias | default "issuer-aes-key-alias" -}}
{{- end -}}

{{/*
Defines Name of the Secret holding the database credentials
*/}}
{{- define "issuer-wallet.datasourceSecretName" -}}
{{- printf "%s-datasource-credentials" (include "issuer-wallet.fullname" .) -}}
{{- end -}}

{{/*
Defines Secret Directory for PSQL Vault
*/}}
{{- define "issuer-wallet.sqlVaultDirectory" -}}
{{- "/opt/wallet/secrets" -}}
{{- end -}}

{{/*
Defines if Hashicorp Vault is used in general
*/}}
{{- define "issuer-wallet.usesVault" -}}
{{- ne .Values.vaultInit.mode "postgres" -}}
{{- end -}}

{{/* 
Defines if the psql-vault AES secret rendering does run 
*/}}
{{- define "issuer-wallet.vaultInit.sqlAesEnabled" -}}
{{- and .Values.vaultInit.enabled (eq .Values.vaultInit.mode "postgres") -}}
{{- end -}}

{{/* 
Defines Vault Token Secret Name for autoInit
*/}}
{{- define "issuer-wallet.appTokenSecretName" -}}
{{- printf "%s-vault-deployment-token" (include "issuer-wallet.fullname" .) -}}
{{- end -}}

{{/*
Defines Vault KV-v2 secret path. Overrides with global, if set.
*/}}
{{- define "issuer-wallet.vault.secretPath" -}}
{{- $global := .Values.global | default dict -}}
{{- dig "vault" "secretPath" .Values.vault.hashicorp.paths.secret $global | trimSuffix "/" -}}
{{- end -}}

{{/*
Defines Vault KV-v2 mount name derived from the secret path: /v1/secret -> secret
*/}}
{{- define "issuer-wallet.vault.kvMount" -}}
{{- include "issuer-wallet.vault.secretPath" . | trimPrefix "/v1/" -}}
{{- end -}}

{{/*
Override local Vault values with globals, if set.
*/}}
{{- define "issuer-wallet.vault.url" -}}
{{- $global := .Values.global | default dict -}}
{{- tpl (dig "vault" "url" .Values.vault.hashicorp.url $global) . -}}
{{- end -}}

{{- define "issuer-wallet.vault.token" -}}
{{- $global := .Values.global | default dict -}}
{{- dig "vault" "token" .Values.vault.hashicorp.token $global -}}
{{- end -}}

{{- define "issuer-wallet.vault.mode" -}}
{{- $global := .Values.global | default dict -}}
{{- dig "vault" "mode" .Values.vaultInit.mode $global -}}
{{- end -}}

{{/* 
Defines if the vault-init job for hashicorp vault does run
*/}}
{{- define "issuer-wallet.vaultInit.jobEnabled" -}}
{{- $mode := include "issuer-wallet.vault.mode" . -}}
{{- and .Values.vaultInit.enabled (has $mode (list "hashicorp-dev" "hashicorp-persistent")) -}}
{{- end -}}

{{- define "issuer-wallet.vault.autoInit.enabled" -}}
{{- $global := .Values.global | default dict -}}
{{- dig "vault" "autoInit" "enabled" .Values.vaultInit.autoInit.enabled $global | toString -}}
{{- end -}}

{{- define "issuer-wallet.vault.autoInit.keysSecretName" -}}
{{- $global := .Values.global | default dict -}}
{{- dig "vault" "autoInit" "keysSecretName" .Values.vaultInit.autoInit.keysSecretName $global -}}
{{- end -}}

{{- define "issuer-wallet.vault.autoInit.auditPath" -}}
{{- $global := .Values.global | default dict -}}
{{- dig "vault" "autoInit" "auditPath" .Values.vaultInit.autoInit.auditPath $global -}}
{{- end -}}

{{/*
Override local PSQL values with globals, if set. 
*/}}
{{- define "issuer-wallet.postgresql.jdbcUrl" -}}
{{- $global := .Values.global | default dict -}}
{{- if dig "postgresql" "host" "" $global -}}
{{- printf "jdbc:postgresql://%s:%v/%s"
      (tpl (dig "postgresql" "host" "" $global) .)
      (dig "postgresql" "port" 5432 $global)
      .Values.postgresql.auth.database -}}
{{- else -}}
{{- tpl .Values.postgresql.jdbcUrl . -}}
{{- end -}}
{{- end -}}