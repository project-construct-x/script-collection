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

from deploy import setup

ENV_FILE = ".env"


def run_start():
    setup()


if __name__ == "__main__":
    run_start()
