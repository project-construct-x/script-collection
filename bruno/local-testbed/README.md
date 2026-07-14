# Local Testbed (Bruno)

[Bruno](https://www.usebruno.com/) collection for onboarding identities and running contract
negotiations and transfers against the local testbed deployment.

## Usage
1. Start the environment first via [`../../docker/local-testbed`](../../docker/local-testbed) (`docker compose up`).
2. In Bruno, choose **Open** (not Import) and select this `local-testbed` folder. Pick **Safe Mode** if prompted.
3. Select the `local-con-x-env` environment in the upper-right corner of the Bruno GUI.
4. Run the `identities` folder first (top to bottom), then the `transactions` requests.

See [`../../docker/local-testbed/README.md`](../../docker/local-testbed/README.md) for the full
walkthrough and important notes (e.g. do not batch-run `transactions/consumer`).
