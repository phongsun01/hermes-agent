# WMO Weather Interpretation Codes (mã thời tiết WMO)

Full reference for interpreting WMO weather codes returned by Open-Meteo API.

## Code categories

| Range | Category | Tiếng Việt |
|-------|----------|------------|
| 0 | Clear sky | Trời trong xanh |
| 1, 2, 3 | Mainly clear, partly cloudy, overcast | Có mây |
| 45, 48 | Fog / depositing rime fog | Sương mù |
| 51, 53, 55 | Drizzle: light, moderate, dense | Mưa phùn |
| 56, 57 | Freezing drizzle: light, dense | Mưa phùn đóng băng |
| 61, 63, 65 | Rain: slight, moderate, heavy | Mưa |
| 66, 67 | Freezing rain: light, heavy | Mưa đóng băng |
| 71, 73, 75 | Snow fall: slight, moderate, heavy | Tuyết rơi |
| 77 | Snow grains | Hạt tuyết |
| 80, 81, 82 | Rain showers: slight, moderate, violent | Mưa rào |
| 85, 86 | Snow showers: slight, heavy | Tuyết rào |
| 95 | Thunderstorm (slight or moderate) | **Giông** |
| 96, 99 | Thunderstorm with hail (slight / heavy) | Giông kèm mưa đá |

## Full table

| Code | English (WMO) | Tiếng Việt | Icon hint |
|------|---------------|------------|-----------|
| 0 | Clear sky | Trong xanh | ☀️ |
| 1 | Mainly clear | Chủ yếu trong | 🌤 |
| 2 | Partly cloudy | Có mây rải rác | ⛅️ |
| 3 | Overcast | U ám / nhiều mây | ☁️ |
| 45 | Fog | Sương mù | 🌫 |
| 48 | Depositing rime fog | Sương mù đóng băng | 🌫❄️ |
| 51 | Drizzle: Light | Mưa phùn nhẹ | 🌦 |
| 53 | Drizzle: Moderate | Mưa phùn vừa | 🌦 |
| 55 | Drizzle: Dense intensity | Mưa phùn dày hạt | 🌧 |
| 56 | Freezing Drizzle: Light | Mưa phùn đóng băng nhẹ | 🌧❄️ |
| 57 | Freezing Drizzle: Dense intensity | Mưa phùn đóng băng dày | 🌧❄️ |
| 61 | Rain: Slight | Mưa nhỏ | 🌦 |
| 63 | Rain: Moderate | Mưa vừa | 🌧 |
| 65 | Rain: Heavy intensity | Mưa to | 🌧💦 |
| 66 | Freezing Rain: Light | Mưa đóng băng nhẹ | 🌧❄️ |
| 67 | Freezing Rain: Heavy intensity | Mưa đóng băng nặng | 🌧❄️ |
| 71 | Snow fall: Slight | Tuyết rơi nhẹ | ❄️ |
| 73 | Snow fall: Moderate | Tuyết rơi vừa | ❄️❄️ |
| 75 | Snow fall: Heavy intensity | Tuyết rơi dày | ❄️💨 |
| 77 | Snow grains | Hạt tuyết | ❄️ |
| 80 | Rain showers: Slight | Mưa rào nhẹ | 🌦 |
| 81 | Rain showers: Moderate | Mưa rào vừa | 🌧 |
| 82 | Rain showers: Violent | Mưa rào to | 🌧💦 |
| 85 | Snow showers: Slight | Tuyết rào nhẹ | ❄️ |
| 86 | Snow showers: Heavy | Tuyết rào dày | ❄️💨 |
| 95 | Thunderstorm: Slight or moderate | **Giông** | ⛈ |
| 96 | Thunderstorm with slight hail | Giông kèm mưa đá nhẹ | ⛈🧊 |
| 99 | Thunderstorm with heavy hail | Giông kèm mưa đá nặng | ⛈🧊💥 |

## Quick Python dict for scripting

```python
wmo_vn = {
    0:'Trong xanh', 1:'Chủ yếu trong', 2:'Có mây', 3:'U ám',
    45:'Sương mù', 48:'Sương mù đóng băng',
    51:'Mưa phùn nhẹ', 53:'Mưa phùn vừa', 55:'Mưa phùn dày',
    56:'Mưa phùn đóng băng nhẹ', 57:'Mưa phùn đóng băng dày',
    61:'Mưa nhỏ', 63:'Mưa vừa', 65:'Mưa to',
    66:'Mưa đóng băng nhẹ', 67:'Mưa đóng băng nặng',
    71:'Tuyết rơi nhẹ', 73:'Tuyết rơi vừa', 75:'Tuyết rơi dày',
    77:'Hạt tuyết', 80:'Mưa rào nhẹ', 81:'Mưa rào vừa', 82:'Mưa rào to',
    85:'Tuyết rào nhẹ', 86:'Tuyết rào dày',
    95:'Giông', 96:'Giông + mưa đá nhẹ', 99:'Giông + mưa đá nặng'
}

# Usage:
# desc = wmo_vn.get(weather_code, f'Mã {weather_code}')
```

## Note for Vietnam

- In Vietnam, code **95 (Thunderstorm)** is the most common code during summer months (May-October), reflecting the tropical monsoon climate with frequent afternoon thunderstorms.
- Codes 61-65 (Rain) and 80-82 (Rain showers) are common year-round in Northern Vietnam (Hạ Long, Hà Nội).
- Vietnam virtually never sees snow codes (71-86, except possibly in Sa Pa or Hoàng Liên Sơn at high elevations).
