---
name: vietnam-data
description: "Vietnamese financial market data and weather/climate data — scrape, extract, and present data from Vietnamese government and financial sources."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [vietnam, market-data, weather, finance, data-retrieval, vietnamese]
---

# Vietnam Data Retrieval

Consolidated skill for retrieving Vietnamese financial market data and weather/climate data from Vietnamese sources.

## When to Use

- User asks for Vietnamese stock market data, index prices, or financial information
- User asks for weather forecasts in Vietnamese cities
- User needs climate data from Vietnamese government sources

## Available Modules

### Vietnam Market Data (`references/vietnam-market-data.md`)
How to find, extract, and present Vietnamese financial market data from various sources (VNDIRECT, CafeF, SSI, HOSE, HNX, VSD).

### Vietnamese Weather Data (`references/vietnamese-weather-data.md`)
How to get weather forecasts and climate data for Vietnamese provinces/cities, including historical records and current conditions.

### Vietnamese Tide Data (`references/vietnamese-tide-data.md`)
Tide (triều cường) data for coastal Vietnamese provinces. Covers:
- HTML-scraping recipes for tide-forecast.com (location slugs, regex, browser fallback)
- Computational lunar-phase fallback (`scripts/tide_estimate.py`) when web sources are blocked
- Icon mapping by height, tidal pattern notes for Gulf of Tonkin / Quảng Ninh area
