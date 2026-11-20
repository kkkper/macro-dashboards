#!/usr/bin/env python3
"""FRED API helper for the US macro radar (sanitized standalone copy).

The API key is read from the FRED_API_KEY environment variable at
runtime. NEVER hardcode a key in this file, in page code, or anywhere
in this repo — keys live server-side only (see README iron rules).

Usage:
  export FRED_API_KEY=...   # server-side only
  python3 fred_fetch.py observations --series CPIAUCSL [--units pch|pc1] [--limit 30]
  python3 fred_fetch.py radar-fetch   # every series the radar needs, one JSON doc
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = "https://api.stlouisfed.org/fred"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")


def get(path, params):
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY environment variable is not set")
    query = urllib.parse.urlencode(
        {k: v for k, v in {**params, "api_key": api_key}.items() if v is not None}
    )
    url = f"{BASE}{path}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "macro-dashboards-fred/1.0"})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def observations(series_id, units=None, limit=30, sort_order="desc"):
    data = get("/series/observations", {
        "series_id": series_id,
        "file_type": "json",
        "units": units,
        "limit": limit,
        "sort_order": sort_order,
    })
    out = []
    for obs in data.get("observations", []):
        if obs.get("value") in (None, ".", ""):
            continue
        out.append({"date": obs["date"], "value": float(obs["value"])})
    return out


def latest_pair(series_id, units=None, limit=30):
    obs = observations(series_id, units=units, limit=limit)
    latest = obs[0] if obs else None
    previous = obs[1] if len(obs) > 1 else None
    return latest, previous, obs


def month_end_points(obs_desc, months=24):
    """obs_desc is newest first. Keep the newest point in each month."""
    seen = {}
    for obs in obs_desc:
        key = obs["date"][:7]
        if key not in seen:
            seen[key] = obs
    keys = sorted(seen)[-months:]
    return [seen[k] for k in keys]


def radar_fetch():
    result = {}

    inflation = {
        "CPIAUCSL": "cpi",
        "CPILFESL": "core_cpi",
        "PCEPI": "pce",
        "PCEPILFE": "core_pce",
        "PPIFIS": "ppi",
        "PPIFES": "core_ppi",
    }
    for series_id, key in inflation.items():
        level_latest, level_prev, _ = latest_pair(series_id, limit=4)
        mom_latest, mom_prev, mom_series = latest_pair(series_id, units="pch", limit=30)
        yoy_latest, _, _ = latest_pair(series_id, units="pc1", limit=4)
        result[key] = {
            "series": series_id,
            "level": level_latest,
            "level_previous": level_prev,
            "mom_pct": mom_latest,
            "mom_previous": mom_prev,
            "yoy_pct": yoy_latest,
            "mom_series_24m": list(reversed(mom_series))[-24:],
        }

    payems_latest, payems_prev, payems_levels = latest_pair("PAYEMS", limit=30)
    changes = []
    levels_asc = list(reversed(payems_levels))
    for i in range(1, len(levels_asc)):
        changes.append({
            "date": levels_asc[i]["date"],
            "value": round(levels_asc[i]["value"] - levels_asc[i - 1]["value"], 1),
        })
    result["nonfarm"] = {
        "series": "PAYEMS",
        "total_thousands": payems_latest,
        "change_thousands": changes[-1] if changes else None,
        "change_previous": changes[-2] if len(changes) > 1 else None,
        "change_series_24m": changes[-24:],
    }

    unrate_latest, unrate_prev, unrate_series = latest_pair("UNRATE", limit=30)
    result["unemployment"] = {
        "series": "UNRATE",
        "rate": unrate_latest,
        "previous": unrate_prev,
        "series_24m": list(reversed(unrate_series))[-24:],
    }

    wage_latest, wage_prev, wage_levels = latest_pair("CES0500000003", limit=4)
    wage_yoy_latest, _, wage_yoy_series = latest_pair("CES0500000003", units="pc1", limit=30)
    wage_mom_latest, _, _ = latest_pair("CES0500000003", units="pch", limit=4)
    result["hourly_earnings"] = {
        "series": "CES0500000003",
        "level_usd": wage_latest,
        "level_previous": wage_prev,
        "mom_pct": wage_mom_latest,
        "yoy_pct": wage_yoy_latest,
        "yoy_series_24m": list(reversed(wage_yoy_series))[-24:],
    }

    claims_latest, claims_prev, claims_weekly = latest_pair("ICSA", limit=120)
    result["initial_claims"] = {
        "series": "ICSA",
        "latest_week": claims_latest,
        "previous_week": claims_prev,
        "monthly_points_24m": month_end_points(claims_weekly, months=24),
    }

    jolts_latest, jolts_prev, jolts_series = latest_pair("JTSJOL", limit=30)
    result["jolts"] = {
        "series": "JTSJOL",
        "openings_thousands": jolts_latest,
        "previous": jolts_prev,
        "series_24m": list(reversed(jolts_series))[-24:],
    }

    gdp_latest, gdp_prev, gdp_series = latest_pair("A191RL1Q225SBEA", limit=10)
    result["gdp"] = {
        "series": "A191RL1Q225SBEA",
        "growth_pct": gdp_latest,
        "previous": gdp_prev,
        "series_8q": list(reversed(gdp_series))[-8:],
    }

    retail_latest, retail_prev, _ = latest_pair("RSAFS", limit=4)
    retail_mom_latest, retail_mom_prev, retail_mom_series = latest_pair("RSAFS", units="pch", limit=30)
    retail_yoy_latest, _, _ = latest_pair("RSAFS", units="pc1", limit=4)
    result["retail_sales"] = {
        "series": "RSAFS",
        "level_millions": retail_latest,
        "level_previous": retail_prev,
        "mom_pct": retail_mom_latest,
        "yoy_pct": retail_yoy_latest,
        "mom_series_24m": list(reversed(retail_mom_series))[-24:],
    }

    upper_latest, _, upper_daily = latest_pair("DFEDTARU", limit=400)
    lower_latest, _, _ = latest_pair("DFEDTARL", limit=4)
    result["fed_funds_target"] = {
        "upper": upper_latest,
        "lower": lower_latest,
    }

    for series_id, key in (("DGS2", "ust_2y"), ("DGS10", "ust_10y")):
        latest, prev, daily = latest_pair(series_id, limit=500)
        result[key] = {
            "series": series_id,
            "yield_pct": latest,
            "previous": prev,
            "month_end_24m": month_end_points(daily, months=24),
        }

    dxy_latest, dxy_prev, dxy_daily = latest_pair("DTWEXBGS", limit=500)
    result["dollar_index"] = {
        "series": "DTWEXBGS",
        "value": dxy_latest,
        "previous": dxy_prev,
        "month_end_24m": month_end_points(dxy_daily, months=24),
    }

    return result


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    obs_parser = sub.add_parser("observations")
    obs_parser.add_argument("--series", required=True)
    obs_parser.add_argument("--units", default=None)
    obs_parser.add_argument("--limit", type=int, default=30)
    sub.add_parser("radar-fetch")
    args = parser.parse_args()

    if args.command == "observations":
        print(json.dumps(observations(args.series, units=args.units, limit=args.limit), indent=2))
    elif args.command == "radar-fetch":
        print(json.dumps(radar_fetch(), indent=2))


if __name__ == "__main__":
    main()
