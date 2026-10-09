{{/*
Defines the key of this chart below global (global.<key>.*) for values that differ per chart.
*/}}
{{- define "conxdc.globalKey" -}}connector{{- end -}}

{{/*
Expand the name of the chart.
*/}}
{{- define "conxdc.name" -}}
{{- default .Chart.Name .Values.nameOverride | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "conxdc.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Control Common labels
*/}}
{{- define "conxdc.labels" -}}
helm.sh/chart: {{ include "conxdc.chart" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.customLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Control Common labels
*/}}
{{- define "conxdc.controlplane.labels" -}}
helm.sh/chart: {{ include "conxdc.chart" . }}
{{ include "conxdc.controlplane.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: edc-controlplane
app.kubernetes.io/part-of: edc
{{- end }}

{{/*
Data Common labels
*/}}
{{- define "conxdc.dataplane.labels" -}}
helm.sh/chart: {{ include "conxdc.chart" . }}
{{ include "conxdc.dataplane.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: edc-dataplane
app.kubernetes.io/part-of: edc
{{- end }}

{{/*
Control Selector labels
*/}}
{{- define "conxdc.controlplane.selectorLabels" -}}
app.kubernetes.io/name: {{ include "conxdc.name" . }}-controlplane
app.kubernetes.io/instance: {{ .Release.Name }}-controlplane
{{- end }}

{{/*
Data Selector labels
*/}}
{{- define "conxdc.dataplane.selectorLabels" -}}
app.kubernetes.io/name: {{ include "conxdc.name" . }}-dataplane
app.kubernetes.io/instance: {{ .Release.Name }}-dataplane
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "conxdc.controlplane.serviceaccount.name" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "conxdc.fullname" . ) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "conxdc.dataplane.serviceaccount.name" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "conxdc.fullname" . ) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Control DSP URL
*/}}
{{- define "conxdc.controlplane.url.protocol" -}}
{{- $host := include "conxdc.controlplane.publicHostname" . -}}
{{- $ingress := index (.Values.controlplane.ingresses | default list) 0 | default dict -}}
{{- if .Values.controlplane.url.protocol }}{{/* if dsp api url has been specified explicitly */}}
{{- .Values.controlplane.url.protocol }}
{{- else if $host }}{{/* public hostname known (chart ingress or external ingress) */}}
{{- /* TLS is assumed unless the chart ingress is enabled without TLS */ -}}
{{- $tls := or (not $ingress.enabled) (($ingress.tls).enabled | default false) -}}
{{- printf "%s://%s" (ternary "https" "http" $tls) $host -}}
{{- else }}{{/* no public hostname: cluster-wide service DNS name */}}
{{- printf "http://%s.%s.svc:%v" (include "conxdc.serviceHostname" (dict "context" $ "plane" "controlplane")) $.Release.Namespace $.Values.controlplane.endpoints.protocol.port -}}
{{- end }}
{{- end }}

{{/*
Validation URL
*/}}
{{- define "conxdc.controlplane.url.validation" -}}
{{- printf "%s/token" ( include "conxdc.controlplane.url.control" $ ) -}}
{{- end }}

{{/*
Control Plane Control URL
*/}}
{{- define "conxdc.controlplane.url.control" -}}
{{- printf "http://%s-controlplane:%v%s" ( include "conxdc.fullname" $ ) $.Values.controlplane.endpoints.control.port $.Values.controlplane.endpoints.control.path -}}
{{- end }}

{{/*
Data Plane Control URL
*/}}
{{- define "conxdc.dataplane.url.control" -}}
{{- printf "http://%s-dataplane:%v%s" ( include "conxdc.fullname" $ ) $.Values.dataplane.endpoints.control.port $.Values.dataplane.endpoints.control.path -}}
{{- end }}

{{/*
Data Public URL
*/}}
{{- define "conxdc.dataplane.url.public" -}}
{{- $host := include "conxdc.dataplane.publicHostname" . -}}
{{- $ingress := index (.Values.dataplane.ingresses | default list) 0 | default dict -}}
{{- $path := .Values.dataplane.endpoints.public.path -}}
{{- if .Values.dataplane.url.public }}{{/* if public api url has been specified explicitly */}}
{{- .Values.dataplane.url.public }}
{{- else if $host }}{{/* public hostname known (chart ingress or external ingress) */}}
{{- $tls := or (not $ingress.enabled) (($ingress.tls).enabled | default false) -}}
{{- printf "%s://%s%s" (ternary "https" "http" $tls) $host $path -}}
{{- else }}{{/* no public hostname: cluster-wide service DNS name */}}
{{- printf "http://%s.%s.svc:%v%s" (include "conxdc.serviceHostname" (dict "context" $ "plane" "dataplane")) $.Release.Namespace $.Values.dataplane.endpoints.public.port $path -}}
{{- end }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "conxdc.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "conxdc.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Defines mapping for RSA Key Aliases
*/}}
{{- define "conxdc.signerAlias" -}}{{ .Values.vaultInit.rsa.privateAlias | default "priv" }}{{- end -}}
{{- define "conxdc.verifierAlias" -}}{{ .Values.vaultInit.rsa.publicAlias | default "pub" }}{{- end -}}

{{/*
Defines the DID of the participant (EDC_PARTICIPANT_ID, EDC_IAM_ISSUER_ID in controlplane and dataplane).
global.participant.did -> iatp.id
*/}}
{{- define "conxdc.participantDid" -}}
{{- $global := .Values.global | default dict -}}
{{- dig "participant" "did" (.Values.iatp.id | default "") $global | required "iatp.id or global.participant.did is required" -}}
{{- end -}}

{{/*
Defines the STS client id. An explicit iatp.sts.oauth.client.id wins, otherwise the DID is used.
*/}}
{{- define "conxdc.stsClientId" -}}
{{- .Values.iatp.sts.oauth.client.id | default (include "conxdc.participantDid" .) -}}
{{- end -}}

{{/*
Defines the public hostname of the controlplane (ingress host, DSP callback address).
controlplane.ingresses[0].hostname -> global.connector.controlplane.hostname
A local value wins, so the defaults of ingresses[].hostname in values.yaml must stay empty.
Not to be confused with the in-cluster hostname (EDC_HOSTNAME), see conxdc.serviceHostname.
*/}}
{{- define "conxdc.controlplane.publicHostname" -}}
{{- $global := .Values.global | default dict -}}
{{- $local := "" -}}
{{- with .Values.controlplane.ingresses }}{{ $local = (index . 0).hostname | default "" }}{{ end -}}
{{- $local | default (dig (include "conxdc.globalKey" .) "controlplane" "hostname" "" $global) -}}
{{- end -}}

{{/*
Defines the public hostname of the dataplane (ingress host, public API URL).
dataplane.ingresses[0].hostname -> global.connector.dataplane.hostname
A local value wins, so the defaults of ingresses[].hostname in values.yaml must stay empty.
Not to be confused with the in-cluster hostname (EDC_HOSTNAME), see conxdc.serviceHostname.
*/}}
{{- define "conxdc.dataplane.publicHostname" -}}
{{- $global := .Values.global | default dict -}}
{{- $local := "" -}}
{{- with .Values.dataplane.ingresses }}{{ $local = (index . 0).hostname | default "" }}{{ end -}}
{{- $local | default (dig (include "conxdc.globalKey" .) "dataplane" "hostname" "" $global) -}}
{{- end -}}

{{/*
Defines the host of an ingress entry of the given plane.
<plane>.ingresses[].hostname -> global.connector.<plane>.hostname
A local value wins, so every entry can carry its own host. Entries without hostname use the global value.
Usage inside range: {{ include "conxdc.ingress.host" (dict "context" $ "item" . "plane" "controlplane") }}
*/}}
{{- define "conxdc.ingress.host" -}}
{{- $global := .context.Values.global | default dict -}}
{{- .item.hostname | default (dig (include "conxdc.globalKey" .context) .plane "hostname" "" $global) -}}
{{- end -}}

{{/*
Defines the name of an ingress resource of the given plane: <fullname>-<plane>-<index>, e.g. user-edc-controlplane-0.
Independent of global values and ingresses[].hostname, so names stay stable and unique.
Usage inside range: {{ include "conxdc.ingress.name" (dict "context" $ "plane" "controlplane" "index" $index) }}
*/}}
{{- define "conxdc.ingress.name" -}}
{{- $base := printf "%s-%s" (include "conxdc.fullname" .context) .plane -}}
{{- printf "%s-%v" ($base | trunc 58 | trimSuffix "-") .index -}}
{{- end -}}

{{/*
Defines the in-cluster hostname of the given plane, used for EDC_HOSTNAME.
It always equals the name of the plane's service (<fullname>-<plane>), therefore it is not configurable.
EDC builds internal URLs from it, e.g. the control API URL used between controlplane and dataplane.
Usage: {{ include "conxdc.serviceHostname" (dict "context" $ "plane" "controlplane") }}
*/}}
{{- define "conxdc.serviceHostname" -}}
{{- printf "%s-%s" (include "conxdc.fullname" .context) .plane | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Defines the id used for the service self registration inside the DID document (TX_EDC_DID_SERVICE_SELF_REGISTRATION_ID).
An explicit iatp.didService.selfRegistration.id wins, otherwise the DID is used.
*/}}
{{- define "conxdc.selfRegistrationId" -}}
{{- .Values.iatp.didService.selfRegistration.id | default (include "conxdc.participantDid" .) -}}
{{- end -}}

{{/*
Validates all values of this chart. Call once, e.g. at the top of configmap-controlplane.yaml:
{{- include "conxdc.validate" . -}}
*/}}
{{- define "conxdc.validate" -}}
{{- include "conxdc.validateVaultInit" (dict "context" . "allowed" (list "hashicorp-dev" "hashicorp-persistent")) -}}
{{- include "conxdc.validatePostgres" . -}}
{{- $_ := include "conxdc.participantDid" . -}}
{{- /* check that the public hostnames are resolvable, they are required for DSP callback and public API */ -}}
{{- if not (include "conxdc.controlplane.publicHostname" .) -}}
  {{- fail "controlplane.ingresses[0].hostname or global.connector.controlplane.hostname is required (DSP callback address)" -}}
{{- end -}}
{{- if not (include "conxdc.dataplane.publicHostname" .) -}}
  {{- fail "dataplane.ingresses[0].hostname or global.connector.dataplane.hostname is required (public API URL)" -}}
{{- end -}}
{{- /* check that every enabled ingress resolves to a host */ -}}
{{- range $plane := list "controlplane" "dataplane" -}}
{{- range $index, $ingress := (index $.Values $plane).ingresses -}}
{{- if and $ingress.enabled (not (include "conxdc.ingress.host" (dict "context" $ "item" $ingress "plane" $plane))) -}}
  {{- fail (printf "%s.ingresses[%d] requires a host: set %s.ingresses[%d].hostname or global.connector.%s.hostname" $plane $index $plane $index $plane) -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- /* check that at least one trusted issuer is configured */ -}}
{{- if not .Values.iatp.trustedIssuers -}}
  {{- fail "iatp.trustedIssuers requires at least one trusted issuer" -}}
{{- end -}}
{{- end -}}