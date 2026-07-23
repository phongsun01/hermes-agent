# Vietnamese Weather & Climate Data

## Quick Check (wttr.in)

```bash
# Text format
curl -sL "https://wttr.in/Halong+Quang+Ninh?format=%C+%t+%h+%w&m"

# JSON format with coordinates (avoid naming collisions)
curl -s "https://wttr.in/20.9505,107.0734?format=j1"
```

**Pitfall:** `Ha+Long+Bay` resolves to Germany. Always use `Halong+Quang+Ninh` or coordinates.

## Extended Forecast (Open-Meteo) — 7-Day Free

```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=20.95&longitude=107.08&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code&timezone=Asia%2FBangkok&forecast_days=7"
```

## Official Data (NCHMF)

`https://nchmf.gov.vn/kttv/` — Browse KHÍ HẬU section. Uses JS, needs browser tools.

## wttr.in JSON Key Naming

- `current_condition[0]` → `temp_C` (with underscore)
- `weather[0].hourly[N]` → `tempC` (NO underscore)
- `FeelsLikeC` is consistent in both contexts

## Support Files

- `references/daily-weather-report-workflow.md` — End-to-end daily report template
- `references/nchmf-storm-forecast-2026.md` — NCHMF storm forecast data
- `references/wmo-weather-codes.md` — WMO code table with Vietnamese
