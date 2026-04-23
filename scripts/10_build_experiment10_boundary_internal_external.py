from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any
from urllib import parse, request

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POI_DIR = ROOT / "data" / "poi"
DEFAULT_ANCHOR_FILE = DEFAULT_POI_DIR / "scenic_anchor_master.csv"
DEFAULT_POI_RAW_FILE = DEFAULT_POI_DIR / "scenic_poi_raw_all.csv"
DEFAULT_BOUNDARY_DIR = DEFAULT_POI_DIR / "boundary"
DEFAULT_BOUNDARY_FILE = DEFAULT_POI_DIR / "scenic_boundary_master.csv"
DEFAULT_POI_ZONED_FILE = DEFAULT_POI_DIR / "scenic_poi_raw_all_zoned.csv"
DEFAULT_ZONE_SUMMARY_FILE = DEFAULT_POI_DIR / "scenic_poi_zone_summary.csv"
DEFAULT_AREA_FILE = DEFAULT_POI_DIR / "scenic_area_summary.csv"
DEFAULT_REPORT_FILE = DEFAULT_POI_DIR / "poi_boundary_report.md"

USER_AGENT = "tourism-poi-boundary/1.0 (local research project)"
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build scenic boundaries, scenic areas, and classify POIs as internal/external."
    )
    parser.add_argument("--poi-dir", type=Path, default=DEFAULT_POI_DIR)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--force-refresh-boundary", action="store_true")
    return parser.parse_args()


def build_headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }


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


def fetch_overpass(query: str, timeout_seconds: float, headers: dict[str, str]) -> dict[str, Any]:
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
    raise RuntimeError(last_error)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def safe_float(value: Any) -> float:
    try:
        if value in ("", None):
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def sanitize_filename(text: str) -> str:
    result = str(text or "").strip()
    for ch in '<>:"/\\|?*':
        result = result.replace(ch, "_")
    return result


def coords_from_geometry_list(geometry: list[dict[str, Any]]) -> list[tuple[float, float]]:
    coords = []
    for point in geometry:
        lat = safe_float(point.get("lat"))
        lng = safe_float(point.get("lon"))
        if pd.isna(lat) or pd.isna(lng):
            continue
        coords.append((lng, lat))
    return coords


def ensure_closed_ring(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not coords:
        return []
    ring = list(coords)
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def assemble_rings(segments: list[list[tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    remaining = [seg[:] for seg in segments if len(seg) >= 2]
    rings: list[list[tuple[float, float]]] = []
    while remaining:
        ring = remaining.pop(0)
        changed = True
        while changed and remaining:
            changed = False
            for idx, seg in enumerate(remaining):
                if ring[-1] == seg[0]:
                    ring = ring + seg[1:]
                elif ring[-1] == seg[-1]:
                    ring = ring + list(reversed(seg[:-1]))
                elif ring[0] == seg[-1]:
                    ring = seg[:-1] + ring
                elif ring[0] == seg[0]:
                    ring = list(reversed(seg[1:])) + ring
                else:
                    continue
                remaining.pop(idx)
                changed = True
                break
        ring = ensure_closed_ring(ring)
        if len(ring) >= 4:
            rings.append(ring)
    return rings


def parse_boundary_payload(
    payload: dict[str, Any],
) -> tuple[list[list[tuple[float, float]]], list[list[tuple[float, float]]], str]:
    elements = payload.get("elements") or []
    if not elements:
        return [], [], "no_payload"
    element = elements[0]
    if element.get("type") == "way":
        geometry = coords_from_geometry_list(element.get("geometry") or [])
        ring = ensure_closed_ring(geometry)
        if len(ring) >= 4:
            return [ring], [], "way_polygon"
        return [], [], "way_no_polygon"

    if element.get("type") == "relation":
        outer_segments: list[list[tuple[float, float]]] = []
        inner_segments: list[list[tuple[float, float]]] = []
        for member in element.get("members") or []:
            geometry = coords_from_geometry_list(member.get("geometry") or [])
            if len(geometry) < 2:
                continue
            role = str(member.get("role") or "")
            if role == "inner":
                inner_segments.append(geometry)
            else:
                outer_segments.append(geometry)
        outer_rings = assemble_rings(outer_segments)
        inner_rings = assemble_rings(inner_segments)
        if outer_rings:
            return outer_rings, inner_rings, "relation_polygon"
        return [], [], "relation_no_polygon"

    return [], [], f"unsupported_{element.get('type')}"


def boundary_query(osm_type: str, osm_id: str) -> str:
    if osm_type == "way":
        return f"[out:json][timeout:120];way({osm_id});out geom;"
    if osm_type == "relation":
        return f"[out:json][timeout:120];relation({osm_id});out geom;"
    raise ValueError(f"Unsupported osm_type: {osm_type}")


def ring_area_m2(ring: list[tuple[float, float]]) -> float:
    if len(ring) < 4:
        return 0.0
    lat0 = sum(lat for _, lat in ring[:-1]) / max(len(ring) - 1, 1)
    cos_lat0 = math.cos(math.radians(lat0))
    scale = 111320.0
    points_xy = [(lng * scale * cos_lat0, lat * 110540.0) for lng, lat in ring]
    area2 = 0.0
    for (x1, y1), (x2, y2) in zip(points_xy, points_xy[1:]):
        area2 += x1 * y2 - x2 * y1
    return abs(area2) / 2.0


def point_in_ring(lng: float, lat: float, ring: list[tuple[float, float]]) -> bool:
    inside = False
    points = ring
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        intersects = ((y1 > lat) != (y2 > lat)) and (
            lng < (x2 - x1) * (lat - y1) / ((y2 - y1) or 1e-12) + x1
        )
        if intersects:
            inside = not inside
    return inside


def point_in_boundary(
    lng: float,
    lat: float,
    outer_rings: list[list[tuple[float, float]]],
    inner_rings: list[list[tuple[float, float]]],
) -> bool:
    if not outer_rings:
        return False
    inside_outer = any(point_in_ring(lng, lat, ring) for ring in outer_rings)
    if not inside_outer:
        return False
    inside_inner = any(point_in_ring(lng, lat, ring) for ring in inner_rings)
    return not inside_inner


def build_boundary_master(
    anchor_df: pd.DataFrame,
    boundary_dir: Path,
    timeout_seconds: float,
    force_refresh: bool,
) -> pd.DataFrame:
    headers = build_headers()
    rows: list[dict[str, Any]] = []
    for _, row in anchor_df.sort_values("official_scenic_id", kind="mergesort").iterrows():
        scenic_name = str(row["scenic_name"])
        scenic_id = str(row["official_scenic_id"])
        osm_type = str(row.get("osm_type") or "")
        osm_id = str(row.get("osm_id") or "")
        boundary_raw_path = boundary_dir / "raw" / f"{sanitize_filename(scenic_name)}_boundary.json"
        boundary_geo_path = boundary_dir / "geojson" / f"{sanitize_filename(scenic_name)}_boundary.geojson"

        outer_rings: list[list[tuple[float, float]]] = []
        inner_rings: list[list[tuple[float, float]]] = []
        boundary_status = "missing"
        boundary_source = ""

        if osm_type in {"way", "relation"} and osm_id:
            if boundary_raw_path.exists() and not force_refresh:
                payload = json.loads(boundary_raw_path.read_text(encoding="utf-8"))
            else:
                payload = fetch_overpass(
                    query=boundary_query(osm_type=osm_type, osm_id=osm_id),
                    timeout_seconds=timeout_seconds,
                    headers=headers,
                )
                write_json(boundary_raw_path, payload)

            outer_rings, inner_rings, boundary_status = parse_boundary_payload(payload)
            boundary_source = f"osm_{osm_type}"
            if outer_rings:
                features = []
                for ring in outer_rings:
                    features.append(
                        {
                            "type": "Feature",
                            "properties": {"ring_role": "outer"},
                            "geometry": {"type": "Polygon", "coordinates": [[list(pt) for pt in ring]]},
                        }
                    )
                for ring in inner_rings:
                    features.append(
                        {
                            "type": "Feature",
                            "properties": {"ring_role": "inner"},
                            "geometry": {"type": "Polygon", "coordinates": [[list(pt) for pt in ring]]},
                        }
                    )
                boundary_geo_path.parent.mkdir(parents=True, exist_ok=True)
                boundary_geo_path.write_text(
                    json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        else:
            boundary_status = "no_polygon_source"
            boundary_source = str(row.get("anchor_source") or "")

        outer_area = sum(ring_area_m2(ring) for ring in outer_rings)
        inner_area = sum(ring_area_m2(ring) for ring in inner_rings)
        scenic_area_m2 = max(outer_area - inner_area, 0.0) if outer_rings else math.nan

        rows.append(
            {
                "official_scenic_id": scenic_id,
                "scenic_name": scenic_name,
                "category_name": str(row.get("category_name") or ""),
                "anchor_source": str(row.get("anchor_source") or ""),
                "resolve_status": str(row.get("resolve_status") or ""),
                "osm_type": osm_type,
                "osm_id": osm_id,
                "boundary_source": boundary_source,
                "boundary_status": boundary_status,
                "outer_ring_n": len(outer_rings),
                "inner_ring_n": len(inner_rings),
                "has_boundary_polygon": int(bool(outer_rings)),
                "scenic_area_m2": round(scenic_area_m2, 2) if not pd.isna(scenic_area_m2) else math.nan,
                "scenic_area_km2": round(scenic_area_m2 / 1_000_000.0, 6) if not pd.isna(scenic_area_m2) else math.nan,
            }
        )
    return pd.DataFrame(rows)


def load_boundary_rings(boundary_geo_path: Path) -> tuple[list[list[tuple[float, float]]], list[list[tuple[float, float]]]]:
    if not boundary_geo_path.exists():
        return [], []
    payload = json.loads(boundary_geo_path.read_text(encoding="utf-8"))
    outer_rings: list[list[tuple[float, float]]] = []
    inner_rings: list[list[tuple[float, float]]] = []
    for feature in payload.get("features") or []:
        role = str((feature.get("properties") or {}).get("ring_role") or "outer")
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Polygon":
            continue
        coords = geometry.get("coordinates") or []
        if not coords:
            continue
        ring = [(safe_float(lng), safe_float(lat)) for lng, lat in coords[0]]
        ring = [(lng, lat) for lng, lat in ring if not pd.isna(lng) and not pd.isna(lat)]
        ring = ensure_closed_ring(ring)
        if len(ring) < 4:
            continue
        if role == "inner":
            inner_rings.append(ring)
        else:
            outer_rings.append(ring)
    return outer_rings, inner_rings


def build_poi_zone_outputs(
    poi_raw_df: pd.DataFrame,
    boundary_master: pd.DataFrame,
    boundary_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    zoned_frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, Any]] = []
    by_scenic_dir = ROOT / "data" / "poi" / "by_scenic"

    for _, boundary_row in boundary_master.sort_values("official_scenic_id", kind="mergesort").iterrows():
        scenic_id = str(boundary_row["official_scenic_id"])
        scenic_name = str(boundary_row["scenic_name"])
        scenic_df = poi_raw_df.loc[poi_raw_df["official_scenic_id"] == scenic_id].copy()
        boundary_geo_path = boundary_dir / "geojson" / f"{sanitize_filename(scenic_name)}_boundary.geojson"
        outer_rings, inner_rings = load_boundary_rings(boundary_geo_path)
        has_boundary = bool(outer_rings)

        if scenic_df.empty:
            continue

        if has_boundary:
            scenic_df["poi_zone"] = scenic_df.apply(
                lambda r: (
                    "internal"
                    if point_in_boundary(
                        lng=safe_float(r["poi_lng"]),
                        lat=safe_float(r["poi_lat"]),
                        outer_rings=outer_rings,
                        inner_rings=inner_rings,
                    )
                    else "external"
                ),
                axis=1,
            )
        else:
            scenic_df["poi_zone"] = "unknown"

        zoned_frames.append(scenic_df)
        for poi_zone, zone_df in scenic_df.groupby("poi_zone", sort=False):
            summary_rows.append(
                {
                    "official_scenic_id": scenic_id,
                    "scenic_name": scenic_name,
                    "category_name": str(boundary_row["category_name"]),
                    "has_boundary_polygon": int(has_boundary),
                    "poi_zone": poi_zone,
                    "poi_n": len(zone_df),
                    "transport_n": int(zone_df["poi_categories"].str.contains("transport", na=False).sum()),
                    "parking_n": int(zone_df["poi_categories"].str.contains("parking", na=False).sum()),
                    "food_retail_n": int(zone_df["poi_categories"].str.contains("food_retail", na=False).sum()),
                    "lodging_n": int(zone_df["poi_categories"].str.contains("lodging", na=False).sum()),
                    "commercial_n": int(zone_df["poi_categories"].str.contains("commercial", na=False).sum()),
                    "public_service_n": int(zone_df["poi_categories"].str.contains("public_service", na=False).sum()),
                    "nearby_attractions_n": int(zone_df["poi_categories"].str.contains("nearby_attractions", na=False).sum()),
                }
            )

        scenic_folder = by_scenic_dir / sanitize_filename(scenic_name)
        scenic_folder.mkdir(parents=True, exist_ok=True)
        write_csv(scenic_df, scenic_folder / f"{sanitize_filename(scenic_name)}_poi_raw_zoned.csv")

    zoned_all = pd.concat(zoned_frames, ignore_index=True) if zoned_frames else pd.DataFrame()
    zone_summary = pd.DataFrame(summary_rows)
    return zoned_all, zone_summary


def build_report(boundary_master: pd.DataFrame, zone_summary: pd.DataFrame, report_file: Path) -> None:
    lines = ["# POI Boundary Report", "", "## 1. Coverage", ""]
    scenic_n = len(boundary_master)
    polygon_n = int(boundary_master["has_boundary_polygon"].fillna(0).sum())
    lines.append(f"- scenic_n: {scenic_n}")
    lines.append(f"- boundary_polygon_n: {polygon_n}")
    lines.append(f"- boundary_polygon_rate: {round(polygon_n / scenic_n, 4) if scenic_n else 0}")
    lines.append("")
    lines.append("## 2. Scenic area summary")
    lines.append("")
    for _, row in boundary_master.sort_values("official_scenic_id", kind="mergesort").iterrows():
        area = row["scenic_area_km2"]
        area_text = f"{area:.4f} km2" if pd.notna(area) else "NA"
        lines.append(
            f"- {row['scenic_name']}: boundary={int(row['has_boundary_polygon'])}, area={area_text}, status={row['boundary_status']}"
        )
    lines.append("")
    lines.append("## 3. Internal / external POI summary")
    lines.append("")
    if not zone_summary.empty:
        for scenic_name, scenic_df in zone_summary.groupby("scenic_name", sort=False):
            parts = []
            for _, row in scenic_df.sort_values("poi_zone", kind="mergesort").iterrows():
                parts.append(f"{row['poi_zone']}={row['poi_n']}")
            lines.append(f"- {scenic_name}: " + ", ".join(parts))
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    poi_dir = args.poi_dir
    anchor_file = poi_dir / "scenic_anchor_master.csv"
    poi_raw_file = poi_dir / "scenic_poi_raw_all.csv"
    boundary_dir = poi_dir / "boundary"
    boundary_file = poi_dir / "scenic_boundary_master.csv"
    poi_zoned_file = poi_dir / "scenic_poi_raw_all_zoned.csv"
    zone_summary_file = poi_dir / "scenic_poi_zone_summary.csv"
    area_file = poi_dir / "scenic_area_summary.csv"
    report_file = poi_dir / "poi_boundary_report.md"

    anchor_df = pd.read_csv(anchor_file)
    poi_raw_df = pd.read_csv(poi_raw_file)
    boundary_master = build_boundary_master(
        anchor_df=anchor_df,
        boundary_dir=boundary_dir,
        timeout_seconds=args.timeout_seconds,
        force_refresh=args.force_refresh_boundary,
    )
    zoned_all, zone_summary = build_poi_zone_outputs(
        poi_raw_df=poi_raw_df,
        boundary_master=boundary_master,
        boundary_dir=boundary_dir,
    )

    if not zoned_all.empty:
        zoned_all = zoned_all.sort_values(["official_scenic_id", "poi_zone", "distance_m"], kind="mergesort").reset_index(drop=True)
    if not zone_summary.empty:
        zone_summary = zone_summary.sort_values(["official_scenic_id", "poi_zone"], kind="mergesort").reset_index(drop=True)

    area_summary = boundary_master[
        [
            "official_scenic_id",
            "scenic_name",
            "category_name",
            "has_boundary_polygon",
            "boundary_status",
            "scenic_area_m2",
            "scenic_area_km2",
        ]
    ].copy()

    write_csv(boundary_master, boundary_file)
    write_csv(zoned_all, poi_zoned_file)
    write_csv(zone_summary, zone_summary_file)
    write_csv(area_summary, area_file)
    build_report(boundary_master=boundary_master, zone_summary=zone_summary, report_file=report_file)

    print(f"boundary_file={boundary_file}")
    print(f"poi_zoned_file={poi_zoned_file}")
    print(f"zone_summary_file={zone_summary_file}")
    print(f"area_file={area_file}")
    print(f"report_file={report_file}")
    print(f"scenic_n={len(boundary_master)}")
    print(f"boundary_polygon_n={int(boundary_master['has_boundary_polygon'].fillna(0).sum())}")


if __name__ == "__main__":
    main()
