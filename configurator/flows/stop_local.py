from config import ConnectorConfig
from deploy import stop

ENV_FILE = ".env"


def run_stop(remove: bool = False) -> None:
    config = ConnectorConfig.from_env(ENV_FILE)
    try:
        stop(remove)
        config.state_path.unlink(missing_ok=True)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    run_stop()
