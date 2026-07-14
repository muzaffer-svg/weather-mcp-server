from mcp.server.fastmcp import FastMCP
import httpx
import os

mcp = FastMCP("weather-server")

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


async def get_coordinates(city: str):
    """Şehir adından enlem/boylam bulur."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(GEOCODE_URL, params={"name": city, "count": 1})
        resp.raise_for_status()
        data = resp.json()
        if not data.get("results"):
            return None
        result = data["results"][0]
        return result["latitude"], result["longitude"], result["name"]


@mcp.tool()
async def get_weather(city: str, days: int = 1) -> str:
    """
    Belirtilen şehir için hava durumu tahminini getirir.

    Args:
        city: Şehir adı (örn: "Konya", "Ankara")
        days: Kaç günlük tahmin isteniyor (1-7 arası, varsayılan 1)
    """
    coords = await get_coordinates(city)
    if coords is None:
        return f"'{city}' için konum bulunamadı."

    lat, lon, resolved_name = coords

    async with httpx.AsyncClient() as client:
        resp = await client.get(FORECAST_URL, params={
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,weathercode",
            "timezone": "auto",
            "forecast_days": min(max(days, 1), 7),
        })
        resp.raise_for_status()
        data = resp.json()

    daily = data["daily"]
    lines = [f"{resolved_name} için hava durumu tahmini:"]
    for i, date in enumerate(daily["time"]):
        max_t = daily["temperature_2m_max"][i]
        min_t = daily["temperature_2m_min"][i]
        lines.append(f"- {date}: {min_t}°C - {max_t}°C")

    return "\n".join(lines)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
