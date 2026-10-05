# Copyright (c) 2026 Bergische Universität Wuppertal
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
#
# Contributors:
#   TMDT der Bergischen Universität Wuppertal

import argparse
import mimetypes
import sys
from pathlib import Path
from urllib.parse import quote, urlparse

from pydantic import ValidationError

from client import ConnectorClient
from config import ConnectorConfig
from util import dsp_endpoint_for_protocol

ENV_FILE = ".env"
LOCAL_FILE_SERVER_CONTAINER = "local-webserver"
CONTENT_TYPE_ALIASES = {
    "json": "application/json",
    "png": "image/png",
    "txt": "text/plain",
}
UPLOADS_DIRECTORY = Path("uploads")


def resolve_publish_source(asset_source: str) -> str:
    parsed = urlparse(asset_source)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return asset_source

    share_dir = (Path.cwd() / "share").resolve()
    source = Path(asset_source).resolve()
    try:
        relative_source = source.relative_to(share_dir)
    except ValueError as exc:
        raise ValueError("source must be an HTTP(S) URL or a file inside share/") from exc
    if not source.is_file():
        raise ValueError(f"source file does not exist: {source}")
    return f"http://{LOCAL_FILE_SERVER_CONTAINER}/{quote(relative_source.as_posix())}"


def resolve_content_type(content_type: str) -> str:
    return CONTENT_TYPE_ALIASES.get(content_type.lower(), content_type)


def select_file(file_path: str | None) -> Path:
    if file_path:
        selected_file = Path(file_path)
        if not selected_file.is_file():
            raise ValueError(f"file does not exist: {selected_file}")
        return selected_file

    uploads_directory = Path.cwd() / UPLOADS_DIRECTORY
    if not uploads_directory.is_dir():
        raise ValueError(f"uploads directory does not exist: {uploads_directory}")

    files = sorted(
        (path for path in uploads_directory.iterdir() if path.is_file()),
        key=lambda path: path.name.lower(),
    )
    if not files:
        raise ValueError(f"uploads directory is empty: {uploads_directory}")

    print("Select a file from uploads/:")
    for index, path in enumerate(files):
        print(f"[{index}] {path.name}")

    while True:
        choice = input(f"Select a file (0-{len(files) - 1}): ")
        try:
            index = int(choice)
        except ValueError:
            print("Please enter a valid integer.")
            continue
        if 0 <= index < len(files):
            return files[index]
        print(f"Index must be between 0 and {len(files) - 1}.")


def command_start(args: argparse.Namespace) -> None:
    if not args.y:
        answer = input(
            "This will start a local EDC deployment using Docker. "
            "\nIf you want to use the library to manage an existing connector stack, use `edc status` to check its connectivity. "
            "\nAre you sure you want to start the local deployment? [yes/No] "
        ).strip().lower()

        if answer not in ("y", "yes", "ok"):
            print("Aborted.")
            return

    if not Path(ENV_FILE).exists():
        print("No environment file found. Run edc config first.")
        return

    from flows.simple_connector_flow import run_start
    run_start()
    print("Startup complete.")


def command_stop(args: argparse.Namespace) -> None:
    if args.remove and not args.y:
        answer = input(
            "This will delete all existing state from the connector. "
            "Are you sure? [yes/No] "
        ).strip().lower()

        if answer not in ("y", "yes", "ok"):
            print("Aborted.")
            return
    from flows.stop_local import run_stop
    run_stop(args.remove)


def command_status(_: argparse.Namespace) -> None:
    if not Path(ENV_FILE).exists():
        print("No environment file found. Run edc config first.")
        return
    config = ConnectorConfig.from_env(ENV_FILE)
    client = ConnectorClient(config)
    client.status()

def command_config(args: argparse.Namespace) -> None:
    from flows.setup import run_setup, show_configuration

    if args.show:
        show_configuration()
        return

    run_setup()

def command_request(args: argparse.Namespace) -> None:
    if not Path(ENV_FILE).exists():
        print("No environment file found. Run edc config first.")
        return
    from flows.request_catalog_and_asset import run_request_asset
    if not args.did or not args.endpoint:
        print("Please specify the peer DID and endpoint to start a request!")
        return
    run_request_asset(peer_did=args.did, peer_dsp=args.endpoint, asset_id=args.assetid)


def command_publish(args: argparse.Namespace) -> None:
    if not Path(ENV_FILE).exists():
        print("No environment file found. Run edc config first.")
        return
    config = ConnectorConfig.from_env(ENV_FILE)
    client = ConnectorClient(config)
    published = client.publish_http_asset(
        label=args.label,
        source_url=resolve_publish_source(args.source),
        content_type=resolve_content_type(args.content_type),
    )
    print("Published asset", published)


def command_unpublish(args: argparse.Namespace) -> None:
    if not Path(ENV_FILE).exists():
        print("No environment file found. Run edc config first.")
        return
    config = ConnectorConfig.from_env(ENV_FILE)
    client = ConnectorClient(config)
    asset_id = args.assetid
    if not asset_id:
        catalog = client.fetch_catalog(
            peer_did=config.participant_did,
            peer_dsp=dsp_endpoint_for_protocol(config.participant_dsp_callback_address, config.protocol),
        )
        print(catalog)
        if not catalog:
            print("No published assets.")
            return
        while True:
            choice = input(f"Select an asset (0-{len(catalog) - 1}): ")
            try:
                index = int(choice)
            except ValueError:
                print("Please enter a valid integer.")
                continue
            if 0 <= index < len(catalog):
                asset_id = catalog.select_offer(index=index).asset_id
                break
            print(f"Index must be between 0 and {len(catalog) - 1}.")

    if not args.y:
        answer = input(f"Unpublish asset {asset_id!r}? Existing contracts and source data remain. [yes/No] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return
    client.unpublish_asset(asset_id)
    catalog = client.fetch_catalog(
        peer_did=config.participant_did,
        peer_dsp=dsp_endpoint_for_protocol(config.participant_dsp_callback_address, config.protocol),
    )
    if any(offer.asset_id == asset_id for offer in catalog):
        raise RuntimeError("Asset is still offered by another contract definition; shared definitions were not changed")
    print(f"Unpublished asset {asset_id}")


def command_send_file(args: argparse.Namespace) -> None:
    if not Path(ENV_FILE).exists():
        print("No environment file found. Run edc config first.")
        return

    selected_file = select_file(args.file)
    config = ConnectorConfig.from_env(ENV_FILE)
    client = ConnectorClient(config)
    catalog = client.fetch_catalog(peer_did=args.did, peer_dsp=args.endpoint)
    print(catalog)

    if args.assetid:
        offer = catalog.select_offer(asset_id=args.assetid)
    else:
        if len(catalog) == 0:
            raise RuntimeError("Peer catalog is empty")
        while True:
            choice = input(f"Select an asset (0-{len(catalog) - 1}): ")
            try:
                index = int(choice)
            except ValueError:
                print("Please enter a valid integer.")
                continue
            if 0 <= index < len(catalog):
                offer = catalog.select_offer(index=index)
                break
            print(f"Index must be between 0 and {len(catalog) - 1}.")

    endpoint = client.negotiate_endpoint_reference(
        peer_did=args.did,
        peer_dsp=args.endpoint,
        offer=offer,
    )
    status, body, content_type = client.send_file_via_endpoint(
        endpoint["endpointData"],
        selected_file,
    )
    if not 200 <= status < 300:
        raise RuntimeError(f"File request failed with HTTP {status}")

    media_type = content_type.split(";", 1)[0].strip().lower()
    extension = mimetypes.guess_extension(media_type) or ".bin"
    output = Path(args.output) if args.output else config.downloads_dir / f"{selected_file.stem}{extension}"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(body)
    print(f"Saved {len(body)} bytes ({content_type}) to {output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="edc", description="Single CLI for Construct-X EDC connector workflows")
    sub = parser.add_subparsers(dest="command", required=True)

    start_p = sub.add_parser("start", help="Start the connector stack")
    start_p.add_argument("-y", action="store_true", help="Confirm execution")
    start_p.set_defaults(func=command_start)

    stop_p = sub.add_parser("stop", help="Stop the connector stack")
    stop_p.add_argument("--remove", action="store_true", help="Removes add containers and state")
    stop_p.add_argument("-y", action="store_true", help="Confirm execution")
    stop_p.set_defaults(func=command_stop)

    status_p = sub.add_parser("status", help="Status of the connector client")
    status_p.set_defaults(func=command_status)

    config_p = sub.add_parser("config", help="Configuration setting wizard")
    config_p.add_argument("-s", "--show", action="store_true", help="Show the current connector configuration")
    config_p.set_defaults(func=command_config)

    publish_p = sub.add_parser("publish", help="Publish an asset")
    publish_p.add_argument("--label", required=True, help="Human-readable asset label")
    publish_p.add_argument("--source", required=True, help="Source URL or path under share/")
    publish_p.add_argument("--content-type", default="application/json", help="json, txt, png, or explicit MIME type")
    publish_p.set_defaults(func=command_publish)

    unpublish_p = sub.add_parser("unpublish", help="Remove an asset's catalog offer without deleting its data")
    unpublish_p.add_argument("--assetid", help="Asset ID; omit for interactive selection from your own catalog")
    unpublish_p.add_argument("-y", action="store_true", help="Skip confirmation")
    unpublish_p.set_defaults(func=command_unpublish)

    request_p = sub.add_parser("request", help="Request catalog and optionally transfer an asset")
    request_p.add_argument("--did", required=True, help="Peer participant DID")
    request_p.add_argument("--endpoint", required=True, help="Peer DSP endpoint/base URL")
    request_p.add_argument("--assetid", help="Select offer by asset ID")
    # request_p.add_argument("--offer-id",  help="Select offer by offer ID")
    request_p.set_defaults(func=command_request)

    send_file_p = sub.add_parser("send-file", help="Send a file to an HTTP asset")
    send_file_p.add_argument("--did", required=True, help="Peer participant DID")
    send_file_p.add_argument("--endpoint", required=True, help="Peer DSP endpoint/base URL")
    send_file_p.add_argument("--assetid", help="Target asset ID; omit for interactive selection")
    send_file_p.add_argument("--file", help="File to send; omit to select from uploads/")
    send_file_p.add_argument("--output", help="Response file; defaults to downloads/<input-name>.<response-type>")
    send_file_p.set_defaults(func=command_send_file)

    return parser


def print_validation_error(exc: ValidationError) -> None:
    print("Connector configuration is invalid:", file=sys.stderr)

    for error in exc.errors():
        message = error["msg"].removeprefix("Value error, ")
        print(message, file=sys.stderr)

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = args.func(args)
        return result if isinstance(result, int) else 0
    except ValidationError as exc:
        print_validation_error(exc)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
