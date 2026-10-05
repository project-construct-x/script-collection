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

from config import ConnectorConfig
from deploy import stop

ENV_FILE = ".env"


def run_stop(remove: bool = False) -> None:
    config = ConnectorConfig.from_env(ENV_FILE)
    try:
        stop(remove)
        if remove:
            config.state_path.unlink(missing_ok=True)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    run_stop()
