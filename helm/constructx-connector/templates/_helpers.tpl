{{/*
Expand the name of the chart.
*/}}
{{- define "conxdc.name" -}}
{{- default .Chart.Name .Values.nameOverride | replace "+" "_"  | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "conxdc.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
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
{{- if .Values.controlplane.url.protocol }}{{/* if dsp api url has been specified explicitly */}}
{{- .Values.controlplane.url.protocol }}
{{- else }}{{/* else when dsp api url has not been specified explicitly */}}
{{- with (index .Values.controlplane.ingresses 0) }}
{{- if .enabled }}{{/* if ingress enabled */}}
{{- if .tls.enabled }}{{/* if TLS enabled */}}
{{- printf "https://%s" .hostname -}}
{{- else }}{{/* else when TLS not enabled */}}
{{- printf "http://%s" .hostname -}}
{{- end }}{{/* end if tls */}}
{{- else }}{{/* else when ingress not enabled */}}
{{- printf "http://%s-controlplane:%v" ( include "conxdc.fullname" $ ) $.Values.controlplane.endpoints.protocol.port -}}
{{- end }}{{/* end if ingress */}}
{{- end }}{{/* end with ingress */}}
{{- end }}{{/* end if .Values.controlplane.url.protocol */}}
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
{{- if .Values.dataplane.url.public }}{{/* if public api url has been specified explicitly */}}
{{- .Values.dataplane.url.public }}
{{- else }}{{/* else when public api url has not been specified explicitly */}}
{{- with (index  .Values.dataplane.ingresses 0) }}
{{- if .enabled }}{{/* if ingress enabled */}}
{{- if .tls.enabled }}{{/* if TLS enabled */}}
{{- printf "https://%s%s" .hostname $.Values.dataplane.endpoints.public.path -}}
{{- else }}{{/* else when TLS not enabled */}}
{{- printf "http://%s%s" .hostname $.Values.dataplane.endpoints.public.path -}}
{{- end }}{{/* end if tls */}}
{{- else }}{{/* else when ingress not enabled */}}
{{- printf "http://%s-dataplane:%v%s" (include "conxdc.fullname" $ ) $.Values.dataplane.endpoints.public.port $.Values.dataplane.endpoints.public.path -}}
{{- end }}{{/* end if ingress */}}
{{- end }}{{/* end with ingress */}}
{{- end }}{{/* end if .Values.dataplane.url.public */}}
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
{{- define "conxdc.signerAlias"   -}}{{ .Values.vaultInit.rsa.privateAlias | default "priv" }}{{- end -}}
{{- define "conxdc.verifierAlias" -}}{{ .Values.vaultInit.rsa.publicAlias | default "pub"  }}{{- end -}}

{{/* 
Defines if the vault-init job for hashicorp vault does run
*/}}
{{- define "conxdc.vaultInit.jobEnabled" -}}
{{- and .Values.vaultInit.enabled (or (eq .Values.vaultInit.mode "hashicorp-dev") (eq .Values.vaultInit.mode "hashicorp-persistent")) -}}
{{- end -}}

{{/* 
Defines Vault Token Secret Name for autoInit
*/}}
{{- define "conxdc.appTokenSecretName" -}}
{{- printf "%s-vault-deployment-token" (include "conxdc.fullname" .) -}}
{{- end -}}