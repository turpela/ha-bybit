# Bybit EU for Home Assistant

Home Assistant add-on repository for **read-only** Bybit EU account reporting: wallet balances, bonus, and recent transactions as sensors. No trading functionality — by design.

## Installation

1. Home Assistant → Settings → Add-ons → Add-on Store → ⋮ → **Repositories**
2. Add: `https://github.com/turpela/ha-bybit`
3. Install **Bybit EU Portfolio**, enter your read-only API key/secret in the Configuration tab, start.

See [bybit_portfolio/DOCS.md](bybit_portfolio/DOCS.md) for full documentation.

## Security

- Only Bybit **EU** endpoint (`api.bybit.eu`) — global keys are not compatible.
- Read-only signed GET requests; no trading endpoints in the codebase.
- API key/secret live in the Supervisor's add-on configuration, never in this repository.
