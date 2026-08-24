# Single Node (Docker)

Minimal Docker Compose setup that starts a single Connector and a single Wallet. This is the smallest
deployment for a participant to run and test their own node.

## Deployment Variants
You can choose between two deployment variants:

### In-Memory Setup
- PostgreSQL runs without persistent storage
- HashiCorp Vault runs in development mode
- No manual Vault initialization required
- All data, secrets, and generated keys are lost when the containers are removed

Recommended for local development, testing, and demonstrations.

### Persistent Setup
- PostgreSQL data is persisted across restarts
- HashiCorp Vault uses persistent file-based storage
- Requires one-time Vault initialization and unsealing
- Database contents, secrets, and generated keys survive container restarts

Recommended for development environments where data persistence is required.

## Prerequisites

Make sure you have...
- ...docker installed on your machine (recommended: version>25.0.4)
- ...a domain for your IP-address
- ...copied [.env.example](./.env.example) to `.env` and changed the secrets
- ...the necessary docker images from [controlplane](https://github.com/project-construct-x/constructx-edc/pkgs/container/con-x-controlplane-postgresql-hashicorp-vault), [dataplane](https://github.com/project-construct-x/constructx-edc/pkgs/container/con-x-dataplane-postgresql-hashicorp-vault), [wallet](https://github.com/project-construct-x/wallet/pkgs/container/wallet)
    - wallet
    - controlplane
    - dataplane
    - Postgres DB
    - HashiCorp Vault


The following values must be configured in the [.env-file](./.env):

- `EMAIL`: Used by Traefik to request and renew TLS certificates from Let's Encrypt.
- `DOMAIN`: Public domain used to expose the Connector, Wallet, and Vault APIs through Traefik.
- `DID`: The DID used by the Connector and Wallet.
- `ISSUER_DID`: DID of the credential issuer.

Example:
```
EMAIL=<YOUR-VALID-EMAIL>
DOMAIN=<YOUR-DOMAIN>
DID=<YOUR-DID>
ISSUER_DID=<ISSUER-DID>
```


## Steps
### Traefik

Traefik acts as a reverse proxy and entry point for all services in this setup.

A public domain is required because the Connector, Wallet, and Vault APIs are exposed through a single hostname. Based on the requested path, Traefik routes incoming requests to the appropriate backend service. It also provisions TLS certificates via Let's Encrypt and redirects HTTP traffic to HTTPS automatically. 

#### Create Network

First run the command `docker network create proxy`

Sample output:
```
35c1364363795...
```

#### Start Traefik 

Run the following command from the current folder to start the traefik container:
```bash
docker compose -f ./traefik/traefik-compose.yaml --env-file ./.env up -d
```

Wait 30 seconds before proceeding with the next steps.

Sample output:
```
[+] Running 1/1
✔ Container traefik Created 
```

## In-Memory Setup

### Start Services

Run `docker compose -f ./connector/docker-compose-memory.yaml --env-file ./.env up -d`

Sample output:
```
[+] Running 7/7
✔ Network network Created
✔ vault Healthy
✔ postgres Healthy 
✔ idhub Created 
✔ vault-init Exited
✔ dataplane Created
✔ controlplane Created
```


### Stop and Remove

1. `docker compose -f ./traefik/traefik-compose.yaml --env-file ./.env down`
2. `docker compose -f ./connector/docker-compose-memory.yaml --env-file ./.env down -v`
3. `docker network rm proxy`

## Persistent Setup

### Security Disclaimer

For convenience, this setup exposes the Vault via a route so that the provided Bruno collection can access secrets and client credentials directly. This configuration is intended for development and testing environments only.

If you do not want the Vault to be externally accessible, remove the Vault route and provide the required secrets through an alternative secure method.

### Initialize Vault (only once)

`docker compose -f ./connector/docker-compose.yaml --env-file ./.env up vault -d`

#### Set the appropriate ownership
The default Vault user inside the Container has the UID `100`.

`sudo chown -R 100:100 ./connector/vault/data`

#### Open a Terminal inside the Container

`docker exec -it vault sh`

Run the following command inside the vault container:

`vault operator init -key-shares=1 -key-threshold=1`

Save the unseal key and the root token. Set the root token in the [.env](./.env) file:

```VAULT_TOKEN=<YOUR-VAULT_TOKEN>```

#### Unseal Vault
Run the following command with the unseal key from the previous step.

`vault operator unseal <unseal-key>`

#### Log in with the root token

`export VAULT_TOKEN=<root-token>`

`vault login`

#### Enable secrets
`vault secrets enable -path=secret kv-v2`

#### Stop Vault

`docker compose -f ./connector/docker-compose.yaml --env-file ./.env down vault -v`

Your Vault is now initialized.

### Start Services
`docker compose -f ./connector/docker-compose.yaml --env-file ./.env up -d`

#### Open a Terminal inside the Container

`docker exec -it vault sh`

#### Unseal Vault
Run the following command with the unseal key.

`vault operator unseal <unseal-key>`


### Stop and Remove
1. `docker compose -f ./traefik/traefik-compose.yaml --env-file ./.env down`
2. `docker compose -f ./connector/docker-compose.yaml --env-file ./.env down -v`
3. `docker network rm proxy`