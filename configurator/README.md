# Construct-X EDC Python Library

Authors:  
Finn Elbl (felbl@uni-wuppertal.de) - TMDT - University of Wuppertal  
Alexander Paulus (paulus@uni-wuppertal.de) - TMDT - University of Wuppertal

`cx_edc_client` is a small Python client for operating one Construct-X
EDC connector and executing common data-exchange workflows. It provides an
application-facing API for connector lifecycle operations, participant
onboarding, asset publication, catalog access, contract negotiation, transfers,
and authorized HTTP requests through Endpoint Data References (EDRs).

It packages a local Docker-based deployment of the essential components of an EDC.

## Features

- Operate a Docker-based connector deployment;
- Publish HTTP assets, policies, and contract definitions;
- Retrieve catalogs and select offers;
- Negotiate contracts;
- Execute pull and `HttpData-PUSH` transfers;

Trusted issuer administration is intentionally excluded. Holder registration,
attestations, and credential definitions remain the responsibility of the
issuer operator.

## Requirements

- Python 3.11 or newer
- Docker with the Compose plugin for lifecycle operations
- Access to a compatible trusted issuer for membership credentials
- Port 443 (and 80 if http is used) of the host machine have to be reachable from the internet
- A valid domain for the machine's IP address

## Setup

### Installation
The python library has to be registered in order for the CLI commands to be available.  
```sh
python -m pip install -e ".[dev]"
```

### Configuration
Create the runtime environment file from the shipped example
```sh
cp .env.example .env
```

Adjust the contained values _before_ starting the connector.

Important settings include:

| Variable                                | Format                                                              | Comment                                                                          |
|-----------------------------------------|---------------------------------------------------------------------|----------------------------------------------------------------------------------|
| `CONNECTOR_DOMAIN`                      | connector.example.org                                               | Public domain of the participants EDC server                                     |
| `ACME_EMAIL`                            | admin@example.org                                                   | Email to retrieve a LetsEncrypt Certificate                                      |
| `PARTICIPANT_DID`                       | did:web:<connector-domain>:<participant-id>                         | DID of the operator participant                                                  |
| `PARTICIPANT_CONTEXT_ID`                | <participant-id>                                                    | Participant context in the wallet                                                |
| `TRUSTED_ISSUER_DID`                    | did:web:<issuer-host>:<issuer-id>                                   | DID of the membership credential issuer.<br/>Provided by the dataspace operator. |
| `ISSUER_CONTEXT`                        | con-x-issuer                                                        | Prodided by the dataspace operator                                               |
| `TRUSTED_ISSUER_CREDENTIAL_SERVICE_URL` | https://<issuer-host>/api/credentials/v1/participants/<issuer-id>   | Provided by the dataspace operator.                                              |
| `TRUSTED_ISSUER_ISSUANCE_SERVICE_URL`   | https://<issuer-host>/api/issuance/v1alpha/participants/<issuer-id> | Provided by the dataspace operator.                                              |

The public paths can be overwritten by uncommenting the respective lines in .env.
If not set explicitly, those values are generated using `CONNECTOR_DOMAIN` as a base URL.

| Variable                             | Format                                                                        | Comment                                                           |
|--------------------------------------|-------------------------------------------------------------------------------|-------------------------------------------------------------------|
| `PARTICIPANT_DSP_CALLBACK_ADDRESS`   | https://<connector-domain>/dsp                                                | Public participant DSP base URL, auto-generated if not set        |
| `PARTICIPANT_DATAPLANE_PUBLIC_URL`   | https://<connector-domain>/public                                             | Public participant dataplane URL, auto-generated if not set       |
| `PARTICIPANT_CREDENTIAL_SERVICE_URL` | https://<connector-domain>/api/credentials/v1/participants/<participant-id>   | Public participant credential endpoint, auto-generated if not set |
| `PARTICIPANT_ISSUER_SERVICE_URL`     | https://<connector-domain>/api/issuance/v1alpha/participants/<participant-id> | Public participant issuance endpoint, auto-generated if not set   |

The following settings should be changed to random secrets

| Variable                       | Format           | Comment                         |
|--------------------------------|------------------|---------------------------------|
| `PARTICIPANT_SECRET_ALIAS`     | <random>         |                                 |
| `POSTGRES_PASSWORD`            | <random>         | Database password               |
| `WALLET_SUPERUSER_KEY`         | YWRtaW4.<random> | Local wallet administration key |
| `VAULT_TOKEN`                  | <random>         | Local Vault token               |
| `CONNECTOR_MANAGEMENT_API_KEY` | <random>         | Control Plane API Key           |

Relative paths are resolved against the current working directory. Placeholder
domains and `change-me` values are rejected before onboarding.

> A guided setup script to create an initial config will be added in a later release.

## Connector Lifecycle

The component functionality is provided through Docker containers.
All containers are automatically started by the library.
>**The used Hashicorp vault is currently being operated in `dev` mode and stores credentials in memory only.
> After a server restart or an EDC shutdown, these values have to be re-initialized!**

The library will detect missing credentials and in most cases restore a working state automatically.

#### Startup

The startup phase consists of these operations:

1. Start Traefik, PostgreSQL, Vault, the Vault initialization job, and the
   participant wallet;
2. Create or reuse the participant context;
3. Store the participant client secret in Vault;
4. Reuse an existing membership credential or request one from the trusted
   issuer;
5. Wait for the credential;
6. Start the Control Plane and Data Plane.

Participant bootstrap state is stored in `.state/participant.json` unless configured otherwise.
This file contains sensitive credentials and must not be committed or shared.

If the python module has been installed (`python -m pip install -e ".[dev]"`), the EDC CLI becomes available via the `edc` command.
**Run this from the base directory, not within `src`!**

Start the connector using:

```bash
edc start
```
This will run all six phases of the startup phase.

#### Data Exchange

Once the connector is running, assets can be published or requested at any time.

Publish an asset:

```bash
edc publish --label "Example Asset" --source http://localhost:8080/api/data
```

where:

- `--label` specifies the human-readable asset name.
- `--source` specifies either an HTTP endpoint or a file located in the `share/` directory.
- `--content-type` optionally specifies the asset's MIME type. Short forms such as `json`, `txt`, and `png` are also supported.

Request assets from another connector:

```bash
edc request --did <participant-did> --endpoint <dsp-endpoint>
```

If no asset is specified, the available catalog entries are displayed and an asset can be selected interactively.

To directly request a specific asset:

```bash
edc request --did <participant-did> --endpoint <dsp-endpoint> --assetid <asset-id>
```

#### Shutdown

Stop the connector stack:

```bash
edc stop
```

> **Warning:** `edc stop --remove` deletes the local connector state (`.state/participant.json`) an all databases, as well as the vault. The connector must be onboarded again before it can participate in data exchange.

## Python Library Usage

All operations are also available separately as part of the ConnectorClient in `src/client.py`.

Refer to the example flows in the `flows` directory for a usage reference.
**Run the flow scripts from the base directory, not within `flows`!**

>Flow scripts can also be executed directly. Modify the default values in each script to the desired endpoints and assets.

### Publish an HTTP Asset

See `flows/publish_asset.py` for an example.

```python
from client import ConnectorClient

client = ConnectorClient()
published = client.publish_http_asset(
    label="Demo asset",
    source_url="https://backend.example.org/data/demo.json",
    asset_id="demo-asset",
)
```

The source URL must be reachable from the provider Data Plane. A fixed asset ID
produces stable policy and contract definition IDs. Existing objects are reused
on HTTP `409`; changed data addresses are not updated automatically.

### Request an Asset

See `flows/request_catalog_and_asset.py` for an example.
For all data transfers, _peer_ refers to the remote EDC while _participant_ refers to the active EDC operator.

```python
from client import ConnectorClient

client = ConnectorClient()
catalog = client.fetch_catalog(peer_did="<peer-did>", peer_dsp="<peer-dsp>")
offer = catalog.select_offer(index=0)
result = client.request_http_asset(
   peer_did="<peer-did>",
   peer_dsp="<peer-dsp>",
   offer=offer,
)
```

## Running the local EDC behind an external proxy

By default, this setup terminates requests with TLS via traefik, using a LetsEncrypt certificate.
In order to operate behind an external proxy that handles TLS, uncomment the following lines in `.env`.

```
#TRAEFIK_ENTRYPOINT=web
#TRAEFIK_BIND_ADDRESS=127.0.0.1
#TRAEFIK_HTTP_PORT=8080
#TRAEFIK_HTTPS_PORT=8443
```

This will disable TLS resolution and set traefik to use HTTP only.
The external proxy can then forward requests to traefik via `HTTP_PORT` and `HTTPS_PORT`.

An example upstream NGINX config would be

```
location / { 
proxy_pass http://127.0.0.1:8080; 
proxy_set_header Host $host; 
proxy_set_header X-Forwarded-Proto https; 
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; 
proxy_http_version 1.1;
}
```

Traefik runs in a closed network by default.
Either add the proxy to the EDC Docker network or add the EDC Docker network to the proxy.

The respective EDC API documentation is available in the [constructx-edc repository](https://github.com/project-construct-x/constructx-edc).
