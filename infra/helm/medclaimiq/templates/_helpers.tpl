{{- define "medclaimiq.name" -}}medclaimiq{{- end -}}
{{- define "medclaimiq.labels" -}}
app.kubernetes.io/name: medclaimiq
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
{{- define "medclaimiq.serviceAccountName" -}}{{ default "medclaimiq" .Values.serviceAccount.name }}{{- end -}}
{{- define "medclaimiq.image" -}}
{{- $img := . -}}
{{- if $img.digest -}}
{{ printf "%s@%s" $img.repository $img.digest }}
{{- else -}}
{{ printf "%s:%s" $img.repository (default "latest" $img.tag) }}
{{- end -}}
{{- end -}}
