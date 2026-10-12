{{/*
Validates the umbrella specific coupling between connector, wallet, Vault and PostgreSQL.
*/}}
{{- define "single-node-connector.validate" -}}
{{- $global := .Values.global | default dict -}}
{{- $connector := index .Values "constructx-connector" | default dict -}}
{{- $wallet := .Values.wallet | default dict -}}

{{- /* 1. Validates that only the connector installs Vault and PostgreSQL */ -}}
{{- if not (and (dig "install" "vault" true $connector) (dig "install" "postgresql" true $connector)) -}}
  {{- fail "constructx-connector.install.vault and .install.postgresql must be true (the connector provides the shared instances)" -}}
{{- end -}}
{{- if or (dig "install" "vault" true $wallet) (dig "install" "postgresql" true $wallet) -}}
  {{- fail "wallet.install.vault and wallet.install.postgresql must be false (the wallet uses the shared instances)" -}}
{{- end -}}

{{- /* 2. Validates that all necessary globals are set and fullnames differ */ -}}
{{- range $key := list "vault.url" "postgresql.host" "connector.fullname" "wallet.fullname" -}}
  {{- $path := splitList "." $key -}}
  {{- if not (dig (index $path 0) (index $path 1) "" $global) -}}
    {{- fail (printf "global.%s is required in the umbrella" $key) -}}
  {{- end -}}
{{- end -}}
{{- if eq (dig "connector" "fullname" "" $global) (dig "wallet" "fullname" "" $global) -}}
  {{- fail "global.connector.fullname and global.wallet.fullname must differ" -}}
{{- end -}}

{{- /* 3. Validates separate databases, customUser must match the wallet database */ -}}
{{- $connectorDb := dig "postgresql" "auth" "database" "edc" $connector -}}
{{- $walletDb := dig "postgresql" "auth" "database" "" $wallet -}}
{{- if eq $connectorDb $walletDb -}}
  {{- fail "constructx-connector.postgresql.auth.database and wallet.postgresql.auth.database must differ" -}}
{{- end -}}
{{- if dig "postgresql" "customUser" "existingSecret" "" $connector -}}
  {{- if ne (dig "postgresql" "customUser" "database" "" $connector) $walletDb -}}
    {{- fail "constructx-connector.postgresql.customUser.database must match wallet.postgresql.auth.database" -}}
  {{- end -}}
{{- end -}}

{{- /* 4. Validates that configured aliases must not collide in the shared secret path */ -}}
{{- $aesAlias := dig "vaultInit" "aes" "alias" "" $wallet -}}
{{- if and $aesAlias (has $aesAlias (list (dig "vaultInit" "rsa" "privateAlias" "priv" $connector) (dig "vaultInit" "rsa" "publicAlias" "pub" $connector))) -}}
  {{- fail "wallet.vaultInit.aes.alias collides with a connector RSA alias in the shared Vault" -}}
{{- end -}}
{{- end -}}