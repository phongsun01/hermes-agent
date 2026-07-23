#!/bin/bash
# Wrapper script for TKB weekly report
cd "$(dirname "$0")"
uv run python tkb_deliver.py week
