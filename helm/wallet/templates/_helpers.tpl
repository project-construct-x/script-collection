{{/*
Defines the key of this chart below global (global.<key>.*) for values that differ per chart.
*/}}
{{- define "wallet.globalKey" -}}wallet{{- end -}}

{{/*
Expand the name of the chart.
*/}}
{{- define "wallet.name" -}}
{{- default .Chart.Name .Values.nameOverride | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "wallet.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Control Common labels
*/}}
{{- define "wallet.labels" -}}
helm.sh/chart: {{ include "wallet.chart" . }}
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
{{- define "wallet.server.labels" -}}
helm.sh/chart: {{ include "wallet.chart" . }}
{{ include "wallet.server.selectorLabels" . }}
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
{{- define "wallet.server.selectorLabels" -}}
app.kubernetes.io/name: {{ include "wallet.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "wallet.server.serviceaccount.name" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "wallet.fullname" . ) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "wallet.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "wallet.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Defines Image depending on chosen Vault Mode
*/}}
{{- define "wallet.image" -}}
{{- $tag := .Values.wallet.image.tag | default .Chart.AppVersion -}}
{{- printf "%s:%s" .Values.wallet.image.repository $tag -}}
{{- end -}}

{{/*
Defines AES-Key-Alias
*/}}
{{- define "wallet.aesKeyAlias" -}}
{{- .Values.vaultInit.aes.alias | default "wallet-aes-key-alias" -}}
{{- end -}}

{{/*
Defines the public hostname of the wallet (default ingress host, public URLs such as the statuslist callback).
wallet.ingresses[0].hostname -> global.wallet.hostname
A local value wins, so the defaults of wallet.ingresses[].hostname in values.yaml must stay empty.
Not to be confused with the in-cluster hostname (EDC_HOSTNAME), see wallet.serviceHostname.
*/}}
{{- define "wallet.publicHostname" -}}
{{- $global := .Values.global | default dict -}}
{{- $local := "" -}}
{{- with .Values.wallet.ingresses }}{{ $local = (index . 0).hostname | default "" }}{{ end -}}
{{- $local | default (dig (include "wallet.globalKey" .) "hostname" "" $global) -}}
{{- end -}}

{{/*
Defines the in-cluster hostname of the wallet, used for EDC_HOSTNAME.
It always equals the name of the service (<fullname>), therefore it is not configurable.
*/}}
{{- define "wallet.serviceHostname" -}}
{{- include "wallet.fullname" . | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Defines the host of an ingress entry.
wallet.ingresses[].hostname -> global.wallet.hostname
A local value wins, so every entry can carry its own host. Entries without hostname use the global value.
Usage inside range: {{ include "wallet.ingress.host" (dict "context" $ "item" .) }}
*/}}
{{- define "wallet.ingress.host" -}}
{{- $global := .context.Values.global | default dict -}}
{{- .item.hostname | default (dig (include "wallet.globalKey" .context) "hostname" "" $global) -}}
{{- end -}}

{{/*
Defines the name of an ingress resource: <fullname>-<index>, e.g. wallet-0.
Independent of global values and ingresses[].hostname, so names stay stable and unique.
Usage inside range: {{ include "wallet.ingress.name" (dict "context" $ "index" $index) }}
*/}}
{{- define "wallet.ingress.name" -}}
{{- printf "%s-%v" (include "wallet.fullname" .context | trunc 58 | trimSuffix "-") .index -}}
{{- end -}}

{{/*
Validates all values of this chart. Call once, e.g. at the top of configmap-runtime.yaml:
{{- include "wallet.validate" . -}}
*/}}
{{- define "wallet.validate" -}}
{{- include "wallet.validateVaultInit" (dict "context" . "allowed" (list "hashicorp-dev" "hashicorp-persistent")) -}}
{{- include "wallet.validatePostgres" . -}}
{{- /* check that every enabled ingress resolves to a host */ -}}
{{- range $index, $ingress := .Values.wallet.ingresses -}}
{{- if and $ingress.enabled (not (include "wallet.ingress.host" (dict "context" $ "item" $ingress))) -}}
  {{- fail (printf "wallet.ingresses[%d] requires a host: set wallet.ingresses[%d].hostname or global.wallet.hostname" $index $index) -}}
{{- end -}}
{{- end -}}
{{- end -}}
