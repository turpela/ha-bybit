# Changelog

## 0.1.1

- Align build with proven ha-kcal-balance pattern: plain `python:3.12-alpine` Dockerfile (no build.yaml/bashio), add `startup: application` and `boot: auto`.

## 0.1.0

- Initial release: wallet balances (total + per coin), bonus, recent transactions from Bybit EU (read-only) pushed as Home Assistant sensors via the Core API.
