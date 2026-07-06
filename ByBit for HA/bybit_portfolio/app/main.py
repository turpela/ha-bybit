"""Bybit EU Portfolio add-on for Home Assistant.

Read-only by design: performs only signed GET requests against the
Bybit EU API (https://api.bybit.eu) and pushes sensor states into
Home Assistant through the Supervisor Core API proxy.

No trading endpoints are used or included.
"""

import hashlib
import hmac
import json
import logging
import os
import signal
import sys
import time
from urllib.parse import urlencode

import requests

BYBIT_BASE_URL = "https://api.bybit.eu"  # Bybit EU — NOT api.bybit.com
HA_CORE_API = "http://supervisor/core/api"
OPTIONS_FILE = "/data/options.json"
RECV_WINDOW = "5000"

_LOGGER = logging.getLogger("bybit_portfolio")
_running = True


def _handle_sigterm(signum, frame):
    global _running
    _LOGGER.info("Received SIGTERM, shutting down gracefully...")
    _running = False


def load_options() -> dict:
    with open(OPTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


class BybitClient:
    """Minimal read-only client for Bybit V5 API (EU endpoint)."""

    def __init__(self, api_key: str, api_secret: str):
        self._key = api_key
        self._secret = api_secret.encode()
        self._session = requests.Session()

    def _get(self, path: str, params: dict) -> dict:
        query = urlencode(sorted(params.items()))
        timestamp = str(int(time.time() * 1000))
        payload = timestamp + self._key + RECV_WINDOW + query
        signature = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()
        headers = {
            "X-BAPI-API-KEY": self._key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": RECV_WINDOW,
            "X-BAPI-SIGN": signature,
        }
        url = f"{BYBIT_BASE_URL}{path}?{query}"
        resp = self._session.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("retCode") != 0:
            raise RuntimeError(
                f"Bybit API error {data.get('retCode')}: {data.get('retMsg')}"
            )
        return data["result"]

    def wallet_balance(self) -> dict:
        """Unified account balance incl. per-coin walletBalance, usdValue, bonus."""
        result = self._get("/v5/account/wallet-balance", {"accountType": "UNIFIED"})
        return result["list"][0] if result.get("list") else {}

    def transaction_log(self, limit: int) -> list:
        """Most recent transactions of the unified account."""
        result = self._get(
            "/v5/account/transaction-log",
            {"accountType": "UNIFIED", "limit": limit},
        )
        return result.get("list", [])


class HomeAssistant:
    """Push sensor states via the Supervisor Core API proxy."""

    def __init__(self):
        token = os.environ.get("SUPERVISOR_TOKEN")
        if not token:
            raise RuntimeError("SUPERVISOR_TOKEN not set — is homeassistant_api enabled?")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self._session = requests.Session()

    def set_state(self, entity_id: str, state, attributes: dict):
        url = f"{HA_CORE_API}/states/{entity_id}"
        resp = self._session.post(
            url,
            headers=self._headers,
            json={"state": str(state), "attributes": attributes},
            timeout=10,
        )
        resp.raise_for_status()


def _round(value, digits=8):
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def publish_balances(ha: HomeAssistant, prefix: str, balance: dict):
    money = {
        "unit_of_measurement": "USD",
        "device_class": "monetary",
        "state_class": "measurement",
        "attribution": "Data from Bybit EU (read-only)",
    }

    ha.set_state(
        f"sensor.{prefix}_total_equity",
        _round(balance.get("totalEquity"), 2),
        {**money, "friendly_name": "Bybit Total Equity", "icon": "mdi:wallet"},
    )
    ha.set_state(
        f"sensor.{prefix}_total_wallet_balance",
        _round(balance.get("totalWalletBalance"), 2),
        {**money, "friendly_name": "Bybit Total Wallet Balance", "icon": "mdi:wallet-outline"},
    )

    total_bonus = 0.0
    for coin in balance.get("coin", []):
        symbol = coin.get("coin", "").lower()
        if not symbol:
            continue
        bonus = _round(coin.get("bonus")) or 0.0
        total_bonus += bonus
        ha.set_state(
            f"sensor.{prefix}_{symbol}_balance",
            _round(coin.get("walletBalance")),
            {
                "friendly_name": f"Bybit {coin.get('coin')} Balance",
                "unit_of_measurement": coin.get("coin"),
                "state_class": "measurement",
                "icon": "mdi:currency-btc" if symbol == "btc" else "mdi:cash",
                "usd_value": _round(coin.get("usdValue"), 2),
                "equity": _round(coin.get("equity")),
                "bonus": bonus,
                "attribution": "Data from Bybit EU (read-only)",
            },
        )

    ha.set_state(
        f"sensor.{prefix}_total_bonus",
        _round(total_bonus),
        {
            "friendly_name": "Bybit Total Bonus",
            "state_class": "measurement",
            "icon": "mdi:gift",
            "attribution": "Data from Bybit EU (read-only)",
        },
    )


def publish_transactions(ha: HomeAssistant, prefix: str, transactions: list):
    latest = transactions[0] if transactions else {}
    recent = [
        {
            "time": tx.get("transactionTime"),
            "type": tx.get("type"),
            "currency": tx.get("currency"),
            "change": tx.get("change"),
            "cash_balance": tx.get("cashBalance"),
        }
        for tx in transactions
    ]
    ha.set_state(
        f"sensor.{prefix}_last_transaction",
        latest.get("type", "none"),
        {
            "friendly_name": "Bybit Last Transaction",
            "icon": "mdi:swap-horizontal",
            "time": latest.get("transactionTime"),
            "currency": latest.get("currency"),
            "change": latest.get("change"),
            "recent_transactions": recent,
            "attribution": "Data from Bybit EU (read-only)",
        },
    )


def main() -> int:
    options = load_options()
    logging.basicConfig(
        level=options.get("log_level", "info").upper(),
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )
    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    api_key = options.get("api_key", "")
    api_secret = options.get("api_secret", "")
    if not api_key or not api_secret:
        _LOGGER.error("api_key and api_secret must be set in the add-on configuration.")
        return 1

    prefix = options.get("sensor_prefix", "bybit").strip().lower() or "bybit"
    interval = int(options.get("poll_interval", 60))
    tx_count = int(options.get("transaction_count", 10))

    bybit = BybitClient(api_key, api_secret)
    ha = HomeAssistant()

    _LOGGER.info(
        "Polling %s every %ss (prefix=%s, transactions=%s)",
        BYBIT_BASE_URL, interval, prefix, tx_count,
    )

    errors = 0
    while _running:
        try:
            publish_balances(ha, prefix, bybit.wallet_balance())
            publish_transactions(ha, prefix, bybit.transaction_log(tx_count))
            errors = 0
            _LOGGER.debug("Update cycle complete.")
        except Exception as err:  # noqa: BLE001
            errors += 1
            _LOGGER.error("Update failed (%s consecutive): %s", errors, err)
            if errors >= 10:
                _LOGGER.error("Too many consecutive failures, exiting.")
                return 1

        # Sleep in 1s slices so SIGTERM is honoured promptly
        for _ in range(interval):
            if not _running:
                break
            time.sleep(1)

    _LOGGER.info("Stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
