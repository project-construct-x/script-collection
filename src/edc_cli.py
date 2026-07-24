import argparse
import sys

from pydantic import ValidationError

from client import ConnectorClient
from config import ConnectorConfig

ENV_FILE = ".env"


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
    config = ConnectorConfig.from_env(ENV_FILE)
    client = ConnectorClient(config)
    client.status()


def command_init(_: argparse.Namespace) -> None:
    print("Initializing the connector is not available yet!")

def command_request(args: argparse.Namespace) -> None:
    from flows.request_catalog_and_asset import run_request_asset
    if not args.did or not args.endpoint:
        print("Please specify the peer DID and endpoint to start a request!")
        return
    run_request_asset(peer_did=args.did, peer_dsp=args.endpoint, asset_id=args.assetid)


def command_publish(args: argparse.Namespace) -> None:
    from flows.publish_asset import run_publish
    run_publish(args.label, args.source)


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

    init_p = sub.add_parser("init", help="Initializes a connector")
    init_p.set_defaults(func=command_init)

    publish_p = sub.add_parser("publish", help="Publish an asset")
    publish_p.add_argument("--label", required=True, help="Human-readable asset label")
    publish_p.add_argument("--source", required=True, help="Source URL or path under share/")
    publish_p.add_argument("--content-type", default="application/json", help="json, txt, png, or explicit MIME type")
    publish_p.set_defaults(func=command_publish)

    request_p = sub.add_parser("request", help="Request catalog and optionally transfer an asset")
    request_p.add_argument("--did", required=True, help="Peer participant DID")
    request_p.add_argument("--endpoint", required=True, help="Peer DSP endpoint/base URL")
    request_p.add_argument("--assetid", help="Select offer by asset ID")
    # request_p.add_argument("--offer-id",  help="Select offer by offer ID")
    request_p.set_defaults(func=command_request)

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
