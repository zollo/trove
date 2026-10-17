{{- define "trove.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "trove.fullname" -}}
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

{{- define "trove.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "trove.labels" -}}
helm.sh/chart: {{ include "trove.chart" . }}
app.kubernetes.io/name: {{ include "trove.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/* Selector labels for one component: include "trove.selectorLabels" (list . "backend") */}}
{{- define "trove.selectorLabels" -}}
{{- $root := index . 0 -}}
app.kubernetes.io/name: {{ include "trove.name" $root }}
app.kubernetes.io/instance: {{ $root.Release.Name }}
app.kubernetes.io/component: {{ index . 1 }}
{{- end }}

{{- define "trove.tag" -}}
{{- .Values.image.tag | default .Chart.AppVersion | default "latest" }}
{{- end }}

{{- define "trove.backendImage" -}}
{{- printf "%s:%s" .Values.image.backend (include "trove.tag" .) }}
{{- end }}

{{- define "trove.frontendImage" -}}
{{- printf "%s:%s" .Values.image.frontend (include "trove.tag" .) }}
{{- end }}

{{- define "trove.secretName" -}}
{{- .Values.existingSecret | default (printf "%s-secrets" (include "trove.fullname" .)) }}
{{- end }}

{{- define "trove.postgresHost" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgres" (include "trove.fullname" .) }}
{{- else }}
{{- required "externalDatabase.host is required when postgresql.enabled is false" .Values.externalDatabase.host }}
{{- end }}
{{- end }}

{{- define "trove.postgresPort" -}}
{{- if .Values.postgresql.enabled }}5432{{ else }}{{ .Values.externalDatabase.port }}{{ end }}
{{- end }}

{{- define "trove.postgresUser" -}}
{{- if .Values.postgresql.enabled }}{{ .Values.postgresql.user }}{{ else }}{{ .Values.externalDatabase.user }}{{ end }}
{{- end }}

{{- define "trove.postgresDatabase" -}}
{{- if .Values.postgresql.enabled }}{{ .Values.postgresql.database }}{{ else }}{{ .Values.externalDatabase.database }}{{ end }}
{{- end }}

{{/* envFrom shared by the backend and the migration init container */}}
{{- define "trove.envFrom" -}}
- configMapRef:
    name: {{ include "trove.fullname" . }}-config
- secretRef:
    name: {{ include "trove.secretName" . }}
{{- end }}

{{/* Restart pods when the chart-managed config or secret changes */}}
{{- define "trove.configChecksum" -}}
checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
{{- if not .Values.existingSecret }}
checksum/secret: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
{{- end }}
{{- end }}
