# Bybit EU Portfolio

Read-only reporting of your Bybit EU account in Home Assistant. No trading functionality exists in this add-on by design — Bybit EU's trading API is restricted to approved brokers, and this project only performs signed GET requests.

## Prerequisites

1. A **Bybit EU** account (`bybit.eu`). This add-on uses `https://api.bybit.eu` — global (`api.bybit.com`) keys will **not** work.
2. A **read-only API key**: Bybit EU → Account → API → Create New Key → System-generated → *Read-Only*, with permissions for **Unified Trading**, **Assets**, and **Earn**.

## Configuration

| Option | Description |
|---|---|
| `api_key` | Your Bybit EU read-only API key |
| `api_secret` | Your API secret (stored by Supervisor, never in the repo) |
| `poll_interval` | Seconds between updates (15–3600, default 60) |
| `transaction_count` | Recent transactions to expose (1–50, default 10) |
| `sensor_prefix` | Entity ID prefix (default `bybit`) |
| `log_level` | `debug` / `info` / `warning` / `error` |

Enter the key and secret in the add-on's Configuration tab. They are stored in the Supervisor's protected add-on config (`/data/options.json` inside the container) and never touch your repository or `configuration.yaml`.

## Sensors

| Entity | State | Attributes |
|---|---|---|
| `sensor.bybit_total_equity` | Total account equity (USD) | — |
| `sensor.bybit_total_wallet_balance` | Total wallet balance (USD) | — |
| `sensor.bybit_<coin>_balance` | Wallet balance per coin (one sensor per held coin) | `usd_value`, `equity`, `bonus` |
| `sensor.bybit_total_bonus` | Sum of per-coin bonus amounts | — |
| `sensor.bybit_last_transaction` | Type of the latest transaction | `time`, `currency`, `change`, `recent_transactions` (list) |

Note: states are pushed via the Home Assistant Core API. They update on every poll but reset to unknown after a Home Assistant restart until the next poll (up to `poll_interval` seconds).

## Troubleshooting

- **`Bybit API error 10003/10004`** — invalid key or signature. Confirm the key was created on **bybit.eu**, not bybit.com.
- **`Bybit API error 10005`** — key lacks permissions. Recreate with Unified Trading + Assets + Earn read permissions.
- **Sensors missing after HA restart** — expected with API-pushed states; they reappear within one poll interval.
- Set `log_level: debug` for request-level logging (secrets are never logged).
