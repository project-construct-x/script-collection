#!/usr/bin/env sh
set -eu

VAULT="${VAULT_ADDR:?missing VAULT_ADDR}"
echo $VAULT
TOKEN="${VAULT_TOKEN:?missing VAULT_TOKEN}"
DP_KEY_PREFIX="${DP_KEY_PREFIX:?missing DP_KEY_PREFIX}"
WALLET_AES_ALIAS="${WALLET_AES_ALIAS:?missing WALLET_AES_ALIAS}"

write_secret() {
  key="$1"
  value="$2"
  jq -n --arg content "$value" '{data:{content:$content}}' |
    curl -fsS \
      -H "X-Vault-Token: $TOKEN" \
      -H "Content-Type: application/json" \
      -X POST \
      --data-binary @- \
      "$VAULT/v1/secret/data/$key" >/dev/null
}

secret_exists() {
  key="$1"
  curl -fsS -H "X-Vault-Token: $TOKEN" \
    "$VAULT/v1/secret/data/$key" >/dev/null 2>&1
}

create_rsa_pair() {
  prefix="$1"
  if secret_exists "${prefix}_priv" && secret_exists "${prefix}_pub"; then
    echo "RSA key pair already exists for $prefix"
    return
  fi

  openssl genrsa -out "/tmp/${prefix}_priv_pkcs1.pem" 2048
  openssl pkcs8 -topk8 -nocrypt \
    -in "/tmp/${prefix}_priv_pkcs1.pem" \
    -out "/tmp/${prefix}_priv.pem"
  openssl rsa \
    -in "/tmp/${prefix}_priv_pkcs1.pem" \
    -pubout \
    -out "/tmp/${prefix}_pub.pem"

  write_secret "${prefix}_priv" "$(cat "/tmp/${prefix}_priv.pem")"
  write_secret "${prefix}_pub" "$(cat "/tmp/${prefix}_pub.pem")"
  rm -f "/tmp/${prefix}_priv_pkcs1.pem" \
    "/tmp/${prefix}_priv.pem" \
    "/tmp/${prefix}_pub.pem"
}

create_aes_key() {
  alias="$1"
  if secret_exists "$alias"; then
    echo "AES key already exists at secret/data/$alias"
    return
  fi

  write_secret "$alias" "$(openssl rand -base64 32 | tr -d '\n')"
}

create_rsa_pair "$DP_KEY_PREFIX"
create_aes_key "$WALLET_AES_ALIAS"

echo "[vault-init] Wallet AES key and Data Plane key pair are ready"
