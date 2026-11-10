# Workshop Issuer

This isolated issuer issues short-lived workshop membership credentials to ten
preassigned DIDs. It uses the wallet's development attestation extension and must
not be used as a production issuer.

## Deployment

The checked-in configuration targets the existing Traefik on the Dataspace VM.
The external Docker network `aas-repository_frontend` must already exist.
Keep the repository layout: the initializer mounts the existing vault init script
from `configurator/docker/vault-init.sh`.

1. Copy `.env.example` to `.env` and generate individual random database, Vault
   and wallet-superuser secrets. The superuser key starts with `YWRtaW4.`.
2. Run `docker compose up -d` in this directory.
3. Add only the public routes below to the existing reverse proxy.
4. Run `python3 bootstrap.py` once to create the issuer participant, definition,
   shared attestation and holder records. The participant API key is stored in
   `.state/issuer.json`; protect and back up that file together with the volumes.

Public DID: `did:web:dataspace.tmdt.uni-wuppertal.de:workshop-issuer`.

| Public path | Internal service |
| --- | --- |
| `/workshop-issuer/did.json` | `http://workshop-issuer-wallet:80/workshop-issuer/did.json` |
| `/workshop-issuer/api/issuance/…` | `http://workshop-issuer-wallet:13132/api/issuance/…` |
| `/workshop-issuer/api/credentials/…` | `http://workshop-issuer-wallet:13131/api/credentials/…` |
| `/workshop-issuer/statuslist/…` | `http://workshop-issuer-wallet:9999/statuslist/…` |

Strip `/workshop-issuer` for the last three routes, but not for the DID document.
Do not publish the identity or issuer administration APIs. They bind only to
loopback ports `30100` and `30200`. Vault and PostgreSQL have no host port mappings.

## Identity Configuration

- Definition: `workshop-membership-v1`
- Type: `https://w3id.org/constructx/credentials/v0.1/MembershipCredential`
- Attestation: `workshop-members`
- Participants: `did:web:teilnehmer01.dataspace-portal.com:participant` through
  `did:web:teilnehmer10.dataspace-portal.com:participant`
- Claims: `workpackages: [4, 5]`, `memberType: external`, `isMember: true`
- Credential lifetime: seven days

The bootstrap does not replace existing definitions or attestations. Inspect
existing objects before changing this configuration. Never run `down -v` on an
issuer whose identities or issued credentials must remain valid.
