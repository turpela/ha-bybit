#!/usr/bin/with-contenv bashio

bashio::log.info "Starting Bybit EU Portfolio add-on..."
exec python3 -u /app/main.py
