#!/bin/bash
# Wrapper script for TKB morning delivery (today)
# The cron scheduler doesn't support script arguments,
# so we use this wrapper to call the main script with the right argument.
cd "$(dirname "$0")"
uv run python tkb_deliver.py today
