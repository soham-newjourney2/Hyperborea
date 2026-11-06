"""P05 step 2: ERA5 daily climate (Open-Meteo archive) for the pilot → rainfall context.

Run:  python -m pipelines.climate
Out:  data/processed/climate_daily.csv, data/processed/climate_summary.json
Label everywhere: modelled reanalysis (ERA5, ~0.25° grid), not station observations.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import geopandas as gpd
import httpx
import pandas as pd
from scipy import stats

from pipelines.osm_common import ROOT

URL = "https://archive-api.open-meteo.com/v1/archive"
START = date(1981, 1, 1)
# IMD daily rainfall categories (mm/day): heavy 64.5–115.5, very heavy 115.6–204.4, extremely heavy ≥ 204.5
IMD = {"heavy": 64.5, "very_heavy": 115.6, "extremely_heavy": 204.5}
OUT = ROOT / "data" / "processed"


def last_full_month_end(today: date) -> date:
    return today.replace(day=1) - timedelta(days=1)


def fetch(lat: float, lon: float, end: date) -> tuple[pd.DataFrame, dict]:
    params = {
        "latitude": lat, "longitude": lon, "start_date": START.isoformat(), "end_date": end.isoformat(),
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min", "timezone": "Asia/Kolkata",
        "models": "era5",
    }
    r = httpx.get(URL, params=params, timeout=120, headers={"User-Agent": "Hyperborea/0.1 (hackathon research)"})
    r.raise_for_status()
    body = r.json()
    df = pd.DataFrame(body["daily"]).rename(columns={"time": "date", "precipitation_sum": "precip_mm",
                                                     "temperature_2m_max": "tmax_c", "temperature_2m_min": "tmin_c"})
    df["date"] = pd.to_datetime(df["date"])
    return df, {"lat": body["latitude"], "lon": body["longitude"], "elevation_m": body.get("elevation")}


def trend(years: pd.Series, values: pd.Series, unit: str) -> dict:
    res = stats.linregress(years, values)
    return {"slope_per_decade": round(res.slope * 10, 2), "p_value": round(res.pvalue, 3), "unit": unit,
            "significant_5pct": bool(res.pvalue < 0.05)}


def summarise(df: pd.DataFrame, grid: dict, end: date) -> dict:
    d = df.assign(year=df.date.dt.year, month=df.date.dt.month)
    full = d[d.year <= (end.year if end.month == 12 else end.year - 1)]  # complete calendar years only
    g = full.groupby("year")
    years = pd.DataFrame({
        "total_mm": g.precip_mm.sum().round(1),
        "jjas_mm": full[full.month.between(6, 9)].groupby("year").precip_mm.sum().round(1),
        "max_1day_mm": g.precip_mm.max().round(1),
        **{f"{k}_days": g.precip_mm.apply(lambda s, t=t: int((s >= t).sum())) for k, t in IMD.items()},
        "tmax_mean_c": g.tmax_c.mean().round(2),
        "tmin_mean_c": g.tmin_c.mean().round(2),
    }).reset_index()
    imax = full.precip_mm.idxmax()
    yrs = years["year"]
    return {
        "source_id": "om_archive",
        "data_status": "modelled",
        "label": "ERA5 reanalysis via Open-Meteo (modelled, ~0.25° grid cell) — not station observations",
        "grid": {**grid, "resolution": "0.25° (ERA5)"},
        "period": {"start": START.isoformat(), "end": end.isoformat(),
                   "full_years": [int(yrs.min()), int(yrs.max())], "n_years": int(len(yrs))},
        "thresholds_mm_day": {**IMD, "source_id": "imd_thresholds"},
        "stats": {
            "annual_total_mean_mm": round(float(years.total_mm.mean()), 1),
            "jjas_share_pct": round(float(100 * years.jjas_mm.sum() / years.total_mm.sum()), 1),
            "max_1day": {"mm": round(float(full.precip_mm.max()), 1), "date": full.loc[imax, "date"].date().isoformat()},
            "annual_max_1day_median_mm": round(float(years.max_1day_mm.median()), 1),
            "heavy_days_per_year_mean": round(float(years.heavy_days.mean()), 2),
        },
        "trends": {
            "annual_total": trend(yrs, years.total_mm, "mm/decade"),
            "annual_max_1day": trend(yrs, years.max_1day_mm, "mm/decade"),
            "heavy_days": trend(yrs, years.heavy_days, "days/decade"),
        },
        "notes": [
            "ERA5 daily totals are grid-cell averages (~25 km); they smooth local convective bursts, so station "
            "records are typically higher. Use as climate context, not as design rainfall.",
            "Annual statistics use complete calendar years only; trends are ordinary least squares on annual values.",
        ],
        "years": years.to_dict("records"),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main() -> None:
    region = gpd.read_file(ROOT / "data" / "curated" / "boundary.geojson").to_crs(32645).centroid.to_crs(4326).iloc[0]
    end = last_full_month_end(date.today())
    df, grid = fetch(region.y, region.x, end)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "climate_daily.csv", index=False, float_format="%.2f")
    summary = summarise(df, grid, end)
    (OUT / "climate_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    s = summary["stats"]
    print(f"{len(df)} days {START}…{end} @ {grid['lat']},{grid['lon']}: mean annual {s['annual_total_mean_mm']} mm, "
          f"JJAS {s['jjas_share_pct']} %, max 1-day {s['max_1day']['mm']} mm on {s['max_1day']['date']}, "
          f"heavy days/yr {s['heavy_days_per_year_mean']}")
    print("trends:", {k: (v["slope_per_decade"], v["p_value"]) for k, v in summary["trends"].items()})


if __name__ == "__main__":
    main()
