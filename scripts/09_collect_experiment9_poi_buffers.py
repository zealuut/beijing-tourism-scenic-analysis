from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any
from urllib import parse, request

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_FILE = ROOT / "data" / "issue_labels" / "experiment4_llm_issue_output_merged.csv"
DEFAULT_POI_DIR = ROOT / "data" / "poi"
DEFAULT_ANCHOR_FILE = DEFAULT_POI_DIR / "scenic_anchor_master.csv"
DEFAULT_RAW_ALL_FILE = DEFAULT_POI_DIR / "scenic_poi_raw_all.csv"
DEFAULT_SUMMARY_ALL_FILE = DEFAULT_POI_DIR / "scenic_poi_summary_all.csv"
DEFAULT_FEATURE_PANEL_FILE = DEFAULT_POI_DIR / "scenic_poi_feature_panel.csv"
DEFAULT_REPORT_FILE = DEFAULT_POI_DIR / "poi_collection_report.md"
DEFAULT_BY_SCENIC_DIR = DEFAULT_POI_DIR / "by_scenic"
DEFAULT_RAW_DIR = DEFAULT_POI_DIR / "raw"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
USER_AGENT = "tourism-poi-collector/1.0 (local research project)"

CATEGORY_ORDER = [
    "transport",
    "parking",
    "food_retail",
    "lodging",
    "commercial",
    "public_service",
    "nearby_attractions",
]
RADIUS_ORDER = [1000, 2000]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect nearby POIs for each scenic spot using a no-key OSM fallback workflow."
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        default=DEFAULT_INPUT_FILE,
        help="Input review table used to derive the current 20 scenic spots.",
    )
    parser.add_argument(
        "--poi-dir",
        type=Path,
        default=DEFAULT_POI_DIR,
        help="Base directory for all POI outputs.",
    )
    parser.add_argument(
        "--radius-list",
        default="1000,2000",
        help="Comma separated radii in meters.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.0,
        help="Delay between external requests.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=120.0,
        help="Per-request timeout.",
    )
    parser.add_argument(
        "--force-refresh-anchor",
        action="store_true",
        help="Ignore cached anchors and geocode again.",
    )
    parser.add_argument(
        "--force-refresh-poi",
        action="store_true",
        help="Ignore cached raw POI JSON and collect again.",
    )
    return parser.parse_args()


def build_headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }


def http_get_json(
    url: str,
    params: dict[str, Any],
    timeout_seconds: float,
    headers: dict[str, str],
) -> Any:
    query = parse.urlencode(params)
    req = request.Request(f"{url}?{query}", headers=headers, method="GET")
    with request.urlopen(req, timeout=timeout_seconds) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def http_post_form_json(
    url: str,
    form_data: dict[str, Any],
    timeout_seconds: float,
    headers: dict[str, str],
) -> Any:
    data = parse.urlencode(form_data).encode("utf-8")
    req_headers = dict(headers)
    req_headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    req = request.Request(url, data=data, headers=req_headers, method="POST")
    with request.urlopen(req, timeout=timeout_seconds) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def safe_float(value: Any) -> float:
    try:
        if value in ("", None):
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def sanitize_filename(text: str) -> str:
    result = str(text or "").strip()
    for ch in '<>:"/\\|?*':
        result = result.replace(ch, "_")
    return result


def normalize_name(text: str) -> str:
    result = str(text or "").strip().lower()
    for token in ["景区", "风景名胜区", "旅游景区", "旅游区", "风景区", "公园", "博物馆", "遗址公园"]:
        result = result.replace(token, "")
    for ch in [" ", "-", "_", "（", "）", "(", ")", "·", "—", "－"]:
        result = result.replace(ch, "")
    return result


def haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    if any(pd.isna(v) for v in [lat1, lng1, lat2, lng2]):
        return math.nan
    radius = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    return 2.0 * radius * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def read_scenic_master(input_file: Path) -> pd.DataFrame:
    df = pd.read_csv(input_file)
    keep_cols = ["official_scenic_id", "scenic_name", "category_name"]
    scenic = df[keep_cols].drop_duplicates().copy()
    scenic = scenic.sort_values(["official_scenic_id", "scenic_name"], kind="mergesort").reset_index(drop=True)
    return scenic


def load_anchor_cache(anchor_file: Path) -> pd.DataFrame:
    if not anchor_file.exists():
        return pd.DataFrame()
    return pd.read_csv(anchor_file)


def geocode_one(
    headers: dict[str, str],
    scenic_name: str,
    timeout_seconds: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    queries = [
        f"{scenic_name}, 北京市, 中国",
        f"北京市{scenic_name}",
        scenic_name,
    ]
    last_candidates: list[dict[str, Any]] = []
    for query in queries:
        payload = http_get_json(
            url=NOMINATIM_URL,
            params={
                "q": query,
                "format": "jsonv2",
                "limit": 5,
                "addressdetails": 1,
                "namedetails": 1,
                "countrycodes": "cn",
            },
            timeout_seconds=timeout_seconds,
            headers=headers,
        )
        if not isinstance(payload, list):
            payload = []
        last_candidates = [item for item in payload if isinstance(item, dict)]
        if last_candidates:
            first = last_candidates[0]
            return {
                "resolve_status": "resolved",
                "anchor_source": "osm_nominatim",
                "query_used": query,
                "display_name": first.get("display_name", ""),
                "osm_type": first.get("osm_type", ""),
                "osm_id": str(first.get("osm_id", "")),
                "lat": safe_float(first.get("lat")),
                "lng": safe_float(first.get("lon")),
            }, last_candidates
        time.sleep(0.4)
    return {
        "resolve_status": "not_found",
        "anchor_source": "osm_nominatim",
        "query_used": queries[-1],
        "display_name": "",
        "osm_type": "",
        "osm_id": "",
        "lat": math.nan,
        "lng": math.nan,
    }, last_candidates


def build_overpass_query(lat: float, lng: float, radius_m: int) -> str:
    body = f"""
[out:json][timeout:120];
(
  node(around:{radius_m},{lat},{lng})["highway"="bus_stop"];
  way(around:{radius_m},{lat},{lng})["highway"="bus_stop"];
  relation(around:{radius_m},{lat},{lng})["highway"="bus_stop"];

  node(around:{radius_m},{lat},{lng})["amenity"="bus_station"];
  way(around:{radius_m},{lat},{lng})["amenity"="bus_station"];
  relation(around:{radius_m},{lat},{lng})["amenity"="bus_station"];

  node(around:{radius_m},{lat},{lng})["public_transport"];
  way(around:{radius_m},{lat},{lng})["public_transport"];
  relation(around:{radius_m},{lat},{lng})["public_transport"];

  node(around:{radius_m},{lat},{lng})["railway"];
  way(around:{radius_m},{lat},{lng})["railway"];
  relation(around:{radius_m},{lat},{lng})["railway"];

  node(around:{radius_m},{lat},{lng})["amenity"~"^(parking|parking_entrance|parking_space)$"];
  way(around:{radius_m},{lat},{lng})["amenity"~"^(parking|parking_entrance|parking_space)$"];
  relation(around:{radius_m},{lat},{lng})["amenity"~"^(parking|parking_entrance|parking_space)$"];

  node(around:{radius_m},{lat},{lng})["amenity"~"^(restaurant|fast_food|cafe|food_court|marketplace|toilets|pharmacy|clinic|hospital|doctors|bank|atm|drinking_water)$"];
  way(around:{radius_m},{lat},{lng})["amenity"~"^(restaurant|fast_food|cafe|food_court|marketplace|toilets|pharmacy|clinic|hospital|doctors|bank|atm|drinking_water)$"];
  relation(around:{radius_m},{lat},{lng})["amenity"~"^(restaurant|fast_food|cafe|food_court|marketplace|toilets|pharmacy|clinic|hospital|doctors|bank|atm|drinking_water)$"];

  node(around:{radius_m},{lat},{lng})["shop"~"^(convenience|supermarket|kiosk|mall|department_store|gift|souvenir)$"];
  way(around:{radius_m},{lat},{lng})["shop"~"^(convenience|supermarket|kiosk|mall|department_store|gift|souvenir)$"];
  relation(around:{radius_m},{lat},{lng})["shop"~"^(convenience|supermarket|kiosk|mall|department_store|gift|souvenir)$"];

  node(around:{radius_m},{lat},{lng})["tourism"~"^(hotel|guest_house|hostel|motel|apartment|attraction|museum|theme_park|zoo|gallery|aquarium|viewpoint|information)$"];
  way(around:{radius_m},{lat},{lng})["tourism"~"^(hotel|guest_house|hostel|motel|apartment|attraction|museum|theme_park|zoo|gallery|aquarium|viewpoint|information)$"];
  relation(around:{radius_m},{lat},{lng})["tourism"~"^(hotel|guest_house|hostel|motel|apartment|attraction|museum|theme_park|zoo|gallery|aquarium|viewpoint|information)$"];
);
out center tags;
"""
    return body.strip()


def fetch_overpass(
    headers: dict[str, str],
    query: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    last_error = ""
    for url in OVERPASS_URLS:
        for attempt in range(1, 4):
            try:
                payload = http_post_form_json(
                    url=url,
                    form_data={"data": query},
                    timeout_seconds=timeout_seconds,
                    headers=headers,
                )
                if not isinstance(payload, dict):
                    raise RuntimeError(f"Unexpected payload type: {type(payload)}")
                return payload
            except Exception as exc:  # noqa: BLE001
                last_error = f"{url} attempt={attempt} error={exc}"
                time.sleep(1.5 * attempt)
    raise RuntimeError(last_error)


def classify_tags(tags: dict[str, Any]) -> tuple[list[str], str]:
    categories: list[str] = []
    detail = "other"

    amenity = str(tags.get("amenity") or "")
    shop = str(tags.get("shop") or "")
    tourism = str(tags.get("tourism") or "")
    railway = str(tags.get("railway") or "")
    highway = str(tags.get("highway") or "")
    public_transport = str(tags.get("public_transport") or "")
    station = str(tags.get("station") or "")

    if (
        highway == "bus_stop"
        or amenity == "bus_station"
        or public_transport in {"platform", "station", "stop_position"}
        or railway in {"station", "halt", "subway_entrance", "tram_stop"}
        or station == "subway"
    ):
        categories.append("transport")
        if station == "subway" or railway == "subway_entrance":
            detail = "subway"
        elif highway == "bus_stop" or amenity == "bus_station":
            detail = "bus"
        else:
            detail = "transport"

    if amenity in {"parking", "parking_entrance", "parking_space"}:
        categories.append("parking")
        if detail == "other":
            detail = "parking"

    if amenity in {"restaurant", "fast_food", "cafe", "food_court"} or shop in {
        "convenience",
        "supermarket",
        "kiosk",
    }:
        categories.append("food_retail")
        if detail == "other":
            detail = "food_retail"

    if tourism in {"hotel", "guest_house", "hostel", "motel", "apartment"}:
        categories.append("lodging")
        if detail == "other":
            detail = "lodging"

    if amenity == "marketplace" or shop in {"mall", "department_store", "gift", "souvenir"}:
        categories.append("commercial")
        if detail == "other":
            detail = "commercial"

    if amenity in {
        "toilets",
        "pharmacy",
        "clinic",
        "hospital",
        "doctors",
        "bank",
        "atm",
        "drinking_water",
    } or tourism == "information":
        categories.append("public_service")
        if detail == "other":
            detail = "public_service"

    if tourism in {"attraction", "museum", "theme_park", "zoo", "gallery", "aquarium", "viewpoint"}:
        categories.append("nearby_attractions")
        if detail == "other":
            detail = "nearby_attractions"

    return sorted(set(categories), key=lambda x: CATEGORY_ORDER.index(x)), detail


def extract_lat_lng(element: dict[str, Any]) -> tuple[float, float]:
    lat = safe_float(element.get("lat"))
    lng = safe_float(element.get("lon"))
    if pd.isna(lat) or pd.isna(lng):
        center = element.get("center") or {}
        lat = safe_float(center.get("lat"))
        lng = safe_float(center.get("lon"))
    return lat, lng


def process_overpass_payload(
    payload: dict[str, Any],
    scenic_row: pd.Series,
    radius_list: list[int],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scenic_name = str(scenic_row["scenic_name"])
    official_scenic_id = str(scenic_row["official_scenic_id"])
    category_name = str(scenic_row["category_name"])
    anchor_lat = safe_float(scenic_row["lat"])
    anchor_lng = safe_float(scenic_row["lng"])
    scenic_name_norm = normalize_name(scenic_name)

    rows: list[dict[str, Any]] = []
    elements = payload.get("elements") or []
    for element in elements:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags") or {}
        if not isinstance(tags, dict):
            tags = {}
        mapped_categories, detail = classify_tags(tags)
        if not mapped_categories:
            continue
        poi_lat, poi_lng = extract_lat_lng(element)
        if pd.isna(poi_lat) or pd.isna(poi_lng):
            continue
        distance_m = haversine_distance_m(anchor_lat, anchor_lng, poi_lat, poi_lng)
        if pd.isna(distance_m):
            continue

        name = str(tags.get("name") or tags.get("brand") or tags.get("operator") or "").strip()
        if name and normalize_name(name) == scenic_name_norm:
            continue

        element_uid = f"{element.get('type', '')}_{element.get('id', '')}"
        rows.append(
            {
                "official_scenic_id": official_scenic_id,
                "scenic_name": scenic_name,
                "category_name": category_name,
                "element_uid": element_uid,
                "element_type": str(element.get("type") or ""),
                "element_id": str(element.get("id") or ""),
                "poi_name": name,
                "poi_detail_type": detail,
                "poi_categories": "|".join(mapped_categories),
                "poi_lat": poi_lat,
                "poi_lng": poi_lng,
                "distance_m": round(distance_m, 2),
                "raw_tags_json": json.dumps(tags, ensure_ascii=False, sort_keys=True),
            }
        )

    raw_df = pd.DataFrame(rows)
    if raw_df.empty:
        summary_df = pd.DataFrame(
            columns=[
                "official_scenic_id",
                "scenic_name",
                "category_name",
                "radius_m",
                "poi_category",
                "poi_count",
                "nearest_distance_m",
            ]
        )
        feature_df = pd.DataFrame(
            [
                build_empty_feature_row(
                    official_scenic_id=official_scenic_id,
                    scenic_name=scenic_name,
                    category_name=category_name,
                    radius_list=radius_list,
                )
            ]
        )
        return raw_df, summary_df, feature_df

    expanded = raw_df.assign(poi_category=raw_df["poi_categories"].str.split("|")).explode("poi_category")
    expanded = expanded.dropna(subset=["poi_category"]).copy()
    expanded["poi_category"] = expanded["poi_category"].astype(str)

    summary_rows: list[dict[str, Any]] = []
    feature_row = build_empty_feature_row(
        official_scenic_id=official_scenic_id,
        scenic_name=scenic_name,
        category_name=category_name,
        radius_list=radius_list,
    )

    for radius_m in radius_list:
        within = expanded.loc[expanded["distance_m"] <= radius_m].copy()
        category_counts = (
            within[["poi_category", "element_uid", "distance_m"]]
            .drop_duplicates(subset=["poi_category", "element_uid"])
            .groupby("poi_category", as_index=False)
            .agg(poi_count=("element_uid", "nunique"), nearest_distance_m=("distance_m", "min"))
        )
        for poi_category in CATEGORY_ORDER:
            matched = category_counts.loc[category_counts["poi_category"] == poi_category]
            if matched.empty:
                poi_count = 0
                nearest_distance_m = math.nan
            else:
                poi_count = safe_int(matched.iloc[0]["poi_count"])
                nearest_distance_m = safe_float(matched.iloc[0]["nearest_distance_m"])
            summary_rows.append(
                {
                    "official_scenic_id": official_scenic_id,
                    "scenic_name": scenic_name,
                    "category_name": category_name,
                    "radius_m": radius_m,
                    "poi_category": poi_category,
                    "poi_count": poi_count,
                    "nearest_distance_m": round(nearest_distance_m, 2) if not pd.isna(nearest_distance_m) else math.nan,
                }
            )
            feature_row[f"{poi_category}_count_{radius_m}m"] = poi_count
            feature_row[f"nearest_{poi_category}_dist_m_{radius_m}m"] = (
                round(nearest_distance_m, 2) if not pd.isna(nearest_distance_m) else math.nan
            )

        feature_row[f"poi_diversity_{radius_m}m"] = int(
            sum(1 for poi_category in CATEGORY_ORDER if feature_row[f"{poi_category}_count_{radius_m}m"] > 0)
        )

    summary_df = pd.DataFrame(summary_rows)
    feature_df = pd.DataFrame([feature_row])
    return raw_df, summary_df, feature_df


def build_empty_feature_row(
    official_scenic_id: str,
    scenic_name: str,
    category_name: str,
    radius_list: list[int],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "official_scenic_id": official_scenic_id,
        "scenic_name": scenic_name,
        "category_name": category_name,
    }
    for radius_m in radius_list:
        for poi_category in CATEGORY_ORDER:
            row[f"{poi_category}_count_{radius_m}m"] = 0
            row[f"nearest_{poi_category}_dist_m_{radius_m}m"] = math.nan
        row[f"poi_diversity_{radius_m}m"] = 0
    return row


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def build_report(
    anchor_df: pd.DataFrame,
    feature_panel: pd.DataFrame,
    summary_all: pd.DataFrame,
    report_file: Path,
    radius_list: list[int],
) -> None:
    lines = ["# Experiment 9 POI Collection Report", "", "## 1. Scope", ""]
    lines.append(f"- scenic_n: {len(anchor_df)}")
    lines.append(f"- resolved_anchor_n: {int(anchor_df['lat'].notna().sum())}")
    lines.append(f"- radius_list_m: {', '.join(str(v) for v in radius_list)}")
    lines.append("")
    lines.append("## 2. POI categories")
    lines.append("")
    lines.extend([f"- {name}" for name in CATEGORY_ORDER])
    lines.append("")
    lines.append("## 3. Scenic summary")
    lines.append("")
    for _, row in feature_panel.sort_values("official_scenic_id", kind="mergesort").iterrows():
        parts = []
        for radius_m in radius_list:
            top = []
            for poi_category in CATEGORY_ORDER:
                value = safe_int(row.get(f"{poi_category}_count_{radius_m}m"), default=0)
                if value > 0:
                    top.append(f"{poi_category}={value}")
            parts.append(f"{radius_m}m[{', '.join(top) if top else 'no_poi'}]")
        lines.append(f"- {row['scenic_name']}: " + " | ".join(parts))
    lines.append("")
    lines.append("## 4. Files")
    lines.append("")
    lines.append(f"- anchor: `{DEFAULT_ANCHOR_FILE}`")
    lines.append(f"- raw_all: `{DEFAULT_RAW_ALL_FILE}`")
    lines.append(f"- summary_all: `{DEFAULT_SUMMARY_ALL_FILE}`")
    lines.append(f"- feature_panel: `{DEFAULT_FEATURE_PANEL_FILE}`")
    lines.append("")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    radius_list = sorted({safe_int(part) for part in str(args.radius_list).split(",") if str(part).strip()})
    radius_list = [value for value in radius_list if value > 0]
    if not radius_list:
        raise ValueError("radius_list must contain positive integers.")

    poi_dir = args.poi_dir
    anchor_file = poi_dir / "scenic_anchor_master.csv"
    raw_all_file = poi_dir / "scenic_poi_raw_all.csv"
    summary_all_file = poi_dir / "scenic_poi_summary_all.csv"
    feature_panel_file = poi_dir / "scenic_poi_feature_panel.csv"
    report_file = poi_dir / "poi_collection_report.md"
    by_scenic_dir = poi_dir / "by_scenic"
    raw_dir = poi_dir / "raw"

    scenic = read_scenic_master(args.input_file)
    anchor_cache = load_anchor_cache(anchor_file)
    if not anchor_cache.empty:
        scenic = scenic.merge(
            anchor_cache[
                [
                    "official_scenic_id",
                    "lat",
                    "lng",
                    "display_name",
                    "anchor_source",
                    "resolve_status",
                    "query_used",
                    "osm_type",
                    "osm_id",
                ]
            ],
            on="official_scenic_id",
            how="left",
        )
    else:
        scenic["lat"] = math.nan
        scenic["lng"] = math.nan
        scenic["display_name"] = ""
        scenic["anchor_source"] = ""
        scenic["resolve_status"] = ""
        scenic["query_used"] = ""
        scenic["osm_type"] = ""
        scenic["osm_id"] = ""

    headers = build_headers()

    geocode_raw_dir = raw_dir / "geocode"
    overpass_raw_dir = raw_dir / "overpass"
    geocode_raw_dir.mkdir(parents=True, exist_ok=True)
    overpass_raw_dir.mkdir(parents=True, exist_ok=True)

    for idx in scenic.index:
        if scenic.at[idx, "lat"] == scenic.at[idx, "lat"] and scenic.at[idx, "lng"] == scenic.at[idx, "lng"] and not args.force_refresh_anchor:
            continue
        scenic_name = str(scenic.at[idx, "scenic_name"])
        result, candidates = geocode_one(headers=headers, scenic_name=scenic_name, timeout_seconds=args.timeout_seconds)
        scenic.at[idx, "lat"] = result["lat"]
        scenic.at[idx, "lng"] = result["lng"]
        scenic.at[idx, "display_name"] = result["display_name"]
        scenic.at[idx, "anchor_source"] = result["anchor_source"]
        scenic.at[idx, "resolve_status"] = result["resolve_status"]
        scenic.at[idx, "query_used"] = result["query_used"]
        scenic.at[idx, "osm_type"] = result["osm_type"]
        scenic.at[idx, "osm_id"] = result["osm_id"]
        raw_path = geocode_raw_dir / f"{sanitize_filename(scenic_name)}_geocode.json"
        write_json(raw_path, {"scenic_name": scenic_name, "result": result, "candidates": candidates})
        write_csv(scenic, anchor_file)
        time.sleep(args.sleep_seconds)

    raw_frames: list[pd.DataFrame] = []
    summary_frames: list[pd.DataFrame] = []
    feature_frames: list[pd.DataFrame] = []

    max_radius = max(radius_list)
    for _, scenic_row in scenic.sort_values("official_scenic_id", kind="mergesort").iterrows():
        scenic_name = str(scenic_row["scenic_name"])
        if pd.isna(scenic_row["lat"]) or pd.isna(scenic_row["lng"]):
            feature_frames.append(
                pd.DataFrame(
                    [
                        build_empty_feature_row(
                            official_scenic_id=str(scenic_row["official_scenic_id"]),
                            scenic_name=scenic_name,
                            category_name=str(scenic_row["category_name"]),
                            radius_list=radius_list,
                        )
                    ]
                )
            )
            continue

        scenic_folder = by_scenic_dir / sanitize_filename(scenic_name)
        scenic_folder.mkdir(parents=True, exist_ok=True)
        overpass_raw_file = overpass_raw_dir / f"{sanitize_filename(scenic_name)}_overpass_{max_radius}m.json"

        if overpass_raw_file.exists() and not args.force_refresh_poi:
            payload = json.loads(overpass_raw_file.read_text(encoding="utf-8"))
        else:
            query = build_overpass_query(
                lat=safe_float(scenic_row["lat"]),
                lng=safe_float(scenic_row["lng"]),
                radius_m=max_radius,
            )
            payload = fetch_overpass(headers=headers, query=query, timeout_seconds=args.timeout_seconds)
            write_json(overpass_raw_file, payload)
            time.sleep(args.sleep_seconds)

        raw_df, summary_df, feature_df = process_overpass_payload(payload=payload, scenic_row=scenic_row, radius_list=radius_list)
        raw_frames.append(raw_df)
        summary_frames.append(summary_df)
        feature_frames.append(feature_df)

        write_csv(raw_df, scenic_folder / f"{sanitize_filename(scenic_name)}_poi_raw.csv")
        write_csv(summary_df, scenic_folder / f"{sanitize_filename(scenic_name)}_poi_summary.csv")

    raw_all = pd.concat(raw_frames, ignore_index=True) if raw_frames else pd.DataFrame()
    summary_all = pd.concat(summary_frames, ignore_index=True) if summary_frames else pd.DataFrame()
    feature_panel = pd.concat(feature_frames, ignore_index=True) if feature_frames else pd.DataFrame()

    if not raw_all.empty:
        raw_all = raw_all.sort_values(["official_scenic_id", "distance_m", "poi_name"], kind="mergesort").reset_index(drop=True)
    if not summary_all.empty:
        summary_all = summary_all.sort_values(["official_scenic_id", "radius_m", "poi_category"], kind="mergesort").reset_index(drop=True)
    if not feature_panel.empty:
        feature_panel = feature_panel.sort_values(["official_scenic_id"], kind="mergesort").reset_index(drop=True)

    write_csv(scenic, anchor_file)
    write_csv(raw_all, raw_all_file)
    write_csv(summary_all, summary_all_file)
    write_csv(feature_panel, feature_panel_file)
    build_report(
        anchor_df=scenic,
        feature_panel=feature_panel,
        summary_all=summary_all,
        report_file=report_file,
        radius_list=radius_list,
    )

    print(f"anchor_file={anchor_file}")
    print(f"raw_all_file={raw_all_file}")
    print(f"summary_all_file={summary_all_file}")
    print(f"feature_panel_file={feature_panel_file}")
    print(f"report_file={report_file}")
    print(f"scenic_n={len(scenic)}")
    print(f"resolved_anchor_n={int(scenic['lat'].notna().sum())}")
    print(f"raw_poi_n={len(raw_all)}")


if __name__ == "__main__":
    main()
