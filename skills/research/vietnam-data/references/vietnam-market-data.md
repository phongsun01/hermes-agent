# Vietnam Market Data Research

## Gold Price Sources

| Source | Works With | Notes |
|--------|-----------|-------|
| `webgia.com/gia-vang/` | curl + browser_navigate | Best tabular data. Unit: đồng/chỉ (×10 for đồng/lượng) |
| `giavang.net/` | browser_navigate | Analysis articles with market drivers |

Cloudflare-blocked sites: SJC, PNJ, DOJI official sites.

## Key Conversion Notes

- 1 lượng = 10 chỉ = 37.5g
- webgia.com prices are in đồng/chỉ — multiply ×10 for đồng/lượng
- giavang.net prices in millions (triệu) per lượng

## Market Analysis Workflow

1. Collect current data (SJC prices, world gold, premium, news)
2. Identify market drivers (geopolitics, Fed, CPI, PBoC buying)
3. Present two scenarios (bullish/bearish) with price targets
4. Add SJC-specific risks (premium, spread, market depth)
5. Always include disclaimer
