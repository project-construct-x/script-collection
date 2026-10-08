{{/*
Defines the key of this chart below global (global.<key>.*) for values that differ per chart.
*/}}
{{- define "issuer-wallet.globalKey" -}}issuerWallet{{- end -}}

{{/*
Expand the name of the chart.
*/}}
{{- define "issuer-wallet.name" -}}
{{- default .Chart.Name .Values.nameOverride | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end }}

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
{{- with .Values.customLabels }}
{{ toYaml . }}
{{- end }}
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
{{- if eq (include "issuer-wallet.vault.mode" .) "postgres" -}}
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
Defines Secret Directory for PSQL Vault
*/}}
{{- define "issuer-wallet.sqlVaultDirectory" -}}
{{- "/opt/wallet/secrets" -}}
{{- end -}}

{{/*
Defines if Hashicorp Vault is used in general
*/}}
{{- define "issuer-wallet.usesVault" -}}
{{- ne (include "issuer-wallet.vault.mode" .) "postgres" -}}
{{- end -}}

{{/*
Defines if the psql-vault AES secret rendering does run
*/}}
{{- define "issuer-wallet.vaultInit.sqlAesEnabled" -}}
{{- and .Values.vaultInit.enabled (eq (include "issuer-wallet.vault.mode" .) "postgres") -}}
{{- end -}}

{{/*
Name of the secret holding the AES key for the SQL vault.
*/}}
{{- define "issuer-wallet.sqlVaultAesSecretName" -}}
{{- printf "%s-sql-vault-aes" (include "issuer-wallet.fullname" .) -}}
{{- end -}}

{{/*
Defines the public hostname of the issuer-wallet (default ingress host, public URLs such as the statuslist callback).
wallet.ingresses[0].hostname -> global.issuerWallet.hostname
A local value wins, so the defaults of wallet.ingresses[].hostname in values.yaml must stay empty.
Not to be confused with the in-cluster hostname (EDC_HOSTNAME), see issuer-wallet.serviceHostname.
*/}}
{{- define "issuer-wallet.publicHostname" -}}
{{- $global := .Values.global | default dict -}}
{{- $local := "" -}}
{{- with .Values.wallet.ingresses }}{{ $local = (index . 0).hostname | default "" }}{{ end -}}
{{- $local | default (dig (include "issuer-wallet.globalKey" .) "hostname" "" $global) -}}
{{- end -}}

{{/*
Defines the in-cluster hostname of the issuer-wallet, used for EDC_HOSTNAME.
It always equals the name of the service (<fullname>), therefore it is not configurable.
*/}}
{{- define "issuer-wallet.serviceHostname" -}}
{{- include "issuer-wallet.fullname" . | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Defines the host of an ingress entry.
wallet.ingresses[].hostname -> global.issuerWallet.hostname
A local value wins, so every entry can carry its own host. Entries without hostname use the global value.
Usage inside range: {{ include "issuer-wallet.ingress.host" (dict "context" $ "item" .) }}
*/}}
{{- define "issuer-wallet.ingress.host" -}}
{{- $global := .context.Values.global | default dict -}}
{{- .item.hostname | default (dig (include "issuer-wallet.globalKey" .context) "hostname" "" $global) -}}
{{- end -}}

{{/*
Defines the name of an ingress resource: <fullname>-<index>, e.g. wallet-0.
Independent of global values and ingresses[].hostname, so names stay stable and unique.
Usage inside range: {{ include "issuer-wallet.ingress.name" (dict "context" $ "index" $index) }}
*/}}
{{- define "issuer-wallet.ingress.name" -}}
{{- printf "%s-%v" (include "issuer-wallet.fullname" .context | trunc 58 | trimSuffix "-") .index -}}
{{- end -}}

{{/*
Validates all values of this chart. Call once, e.g. at the top of configmap-runtime.yaml:
{{- include "issuer-wallet.validate" . -}}
vaultInit.mode=postgres only exists in this chart, so its check lives here and not in _validate.tpl.
*/}}
{{- define "issuer-wallet.validate" -}}
{{- include "issuer-wallet.validateVaultInit" (dict "context" . "allowed" (list "hashicorp-dev" "hashicorp-persistent" "postgres")) -}}
{{- /* check values for inconsistency with mode postgres */ -}}
{{- if and (eq (include "issuer-wallet.vault.mode" .) "postgres") .Values.install.vault -}}
  {{- fail "vaultInit.mode=postgres requires install.vault=false" -}}
{{- end -}}
{{- include "issuer-wallet.validatePostgres" . -}}
{{- /* check that every enabled ingress resolves to a host */ -}}
{{- range $index, $ingress := .Values.wallet.ingresses -}}
{{- if and $ingress.enabled (not (include "issuer-wallet.ingress.host" (dict "context" $ "item" $ingress))) -}}
  {{- fail (printf "wallet.ingresses[%d] requires a host: set wallet.ingresses[%d].hostname or global.issuerWallet.hostname" $index $index) -}}
{{- end -}}
{{- end -}}
{{- end -}}
