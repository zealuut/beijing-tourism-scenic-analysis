#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib import error, request

import pandas as pd
import yaml


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_DIR / "data" / "rawdata" / "experiment2_lda_评分分层300条汇总大表.csv"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "data" / "issue_labels"
DEFAULT_PREPARED_INPUT_PATH = DEFAULT_OUTPUT_DIR / "experiment4_llm_issue_input_6000.csv"
DEFAULT_OUTPUT_CSV = DEFAULT_OUTPUT_DIR / "experiment4_llm_issue_output.csv"
DEFAULT_MERGED_OUTPUT_CSV = DEFAULT_OUTPUT_DIR / "experiment4_llm_issue_output_merged.csv"
DEFAULT_REVIEW_SAMPLE_CSV = DEFAULT_OUTPUT_DIR / "experiment4_llm_issue_review_sample_60.csv"
DEFAULT_OVERALL_SUMMARY_CSV = DEFAULT_OUTPUT_DIR / "experiment4_llm_issue_overall_summary.csv"
DEFAULT_SCENIC_SUMMARY_CSV = DEFAULT_OUTPUT_DIR / "experiment4_llm_issue_scenic_summary.csv"
DEFAULT_PROMPT_PATH = PROJECT_DIR / "prompts" / "llm_issue_tag_prompt_v1.md"
DEFAULT_FEWSHOT_PATH = PROJECT_DIR / "prompts" / "llm_issue_tag_fewshot_v1.md"
DEFAULT_LABEL_YAML = PROJECT_DIR / "dicts" / "issue_label_boundaries_v3.yaml"

DEFAULT_API_URL = "https://api.siliconflow.cn/v1/chat/completions"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V3.2"
DEFAULT_TIMEOUT = 90
DEFAULT_MAX_WORKERS = 2
DEFAULT_PROMPT_VERSION = "issue_only_v1"
DEFAULT_REVIEW_SAMPLE_SIZE = 60


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run experiment 4 issue-tag-only LLM labeling on the 6000-row corpus.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_DIR)
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--prepared-input-csv", type=Path, default=DEFAULT_PREPARED_INPUT_PATH)
    parser.add_argument("--prompt-template", type=Path, default=DEFAULT_PROMPT_PATH)
    parser.add_argument("--fewshot-md", type=Path, default=DEFAULT_FEWSHOT_PATH)
    parser.add_argument("--label-yaml", type=Path, default=DEFAULT_LABEL_YAML)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--merged-output-csv", type=Path, default=DEFAULT_MERGED_OUTPUT_CSV)
    parser.add_argument("--review-sample-csv", type=Path, default=DEFAULT_REVIEW_SAMPLE_CSV)
    parser.add_argument("--overall-summary-csv", type=Path, default=DEFAULT_OVERALL_SUMMARY_CSV)
    parser.add_argument("--scenic-summary-csv", type=Path, default=DEFAULT_SCENIC_SUMMARY_CSV)
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--api-key-env", default="SILICONFLOW_API_KEY")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS)
    parser.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION)
    parser.add_argument("--review-sample-size", type=int, default=DEFAULT_REVIEW_SAMPLE_SIZE)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    return parser.parse_args()


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_labels(path: Path) -> Dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def sanitize_review_text(text: object) -> str:
    return " ".join(str(text or "").split())


def split_issue_tags(value: object) -> List[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        raw_values = value
    else:
        text = str(value).strip()
        if not text or text.lower() == "nan":
            return []
        for sep in [",", ";", "，", "；", "、", "/", "\\", "|"]:
            text = text.replace(sep, "|")
        raw_values = text.split("|")

    seen: set[str] = set()
    normalized: List[str] = []
    for raw in raw_values:
        tag = str(raw).strip().strip('"').strip("'")
        if tag and tag not in seen:
            normalized.append(tag)
            seen.add(tag)
    return normalized


def normalize_issue_tags(value: object, allowed_tags: Iterable[str]) -> List[str]:
    allowed = set(allowed_tags)
    return [tag for tag in split_issue_tags(value) if tag in allowed]


def extract_json_object(text: str) -> str:
    cleaned = str(text).strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    if start == -1:
        raise ValueError("No JSON object start found in model response.")

    depth = 0
    for idx in range(start, len(cleaned)):
        char = cleaned[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start : idx + 1]
    raise ValueError("No complete JSON object found in model response.")


def parse_response_content(content: str, allowed_tags: Iterable[str]) -> Tuple[List[str], str]:
    json_text = extract_json_object(content)
    payload = json.loads(json_text)
    issue_tags = normalize_issue_tags(payload.get("issue_tags", []), allowed_tags)
    reason = " ".join(str(payload.get("reason", "")).split())
    return issue_tags, reason


def build_prompt(template_text: str, fewshot_text: str, label_data: Dict[str, object], row: pd.Series) -> str:
    label_list = ", ".join(label_data["label_order"])
    label_definitions = []
    for tag in label_data["label_order"]:
        spec = label_data["labels"][tag]
        label_definitions.append(f"- {tag} ({spec['name_cn']}): {spec['definition']}")

    prompt = template_text
    prompt = prompt.replace("{{LABEL_LIST}}", label_list)
    prompt = prompt.replace("{{LABEL_DEFINITIONS}}", "\n".join(label_definitions))
    prompt = prompt.replace("{{FEWSHOT_EXAMPLES}}", fewshot_text)
    prompt = prompt.replace("{{REVIEW_ID}}", str(row["review_id"]))
    prompt = prompt.replace("{{SCENIC_NAME}}", str(row["scenic_name"]))
    prompt = prompt.replace("{{REVIEW_TEXT}}", sanitize_review_text(row["review_text"]))
    return prompt


def call_model(
    api_url: str,
    api_key: str,
    model: str,
    prompt: str,
    timeout: int,
    max_retries: int = 4,
) -> Dict[str, object]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 260,
        "stream": False,
    }
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            req = request.Request(api_url, data=encoded, headers=headers, method="POST")
            with request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
            return json.loads(body)
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            last_error = RuntimeError(f"HTTP {exc.code}: {detail[:400]}")
        except Exception as exc:  # noqa: BLE001
            last_error = exc

        if attempt == max_retries:
            break
        time.sleep(min(12, 2 ** (attempt - 1)))

    raise RuntimeError(f"LLM request failed: {last_error}") from last_error


def prepare_input_table(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.copy()
    df["review_id"] = df["comment_id"].fillna("").astype(str)
    df["official_scenic_id"] = df["slot_id"].fillna("").astype(str)
    df["review_text"] = df["review_text"].fillna("").astype(str).str.strip()
    df["row_key"] = df["official_scenic_id"] + "__" + df["review_id"]
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    return df


def label_one_row(
    row: pd.Series,
    api_url: str,
    api_key: str,
    model: str,
    prompt: str,
    label_order: List[str],
    timeout: int,
    prompt_version: str,
) -> Dict[str, object]:
    response_json = call_model(
        api_url=api_url,
        api_key=api_key,
        model=model,
        prompt=prompt,
        timeout=timeout,
    )
    content = response_json["choices"][0]["message"]["content"]
    issue_tags, reason = parse_response_content(content, label_order)

    return {
        "row_key": str(row["row_key"]),
        "review_id": str(row["review_id"]),
        "official_scenic_id": str(row["official_scenic_id"]),
        "scenic_name": str(row["scenic_name"]),
        "review_time": row["review_time"],
        "rating": row["rating"],
        "review_text": sanitize_review_text(row["review_text"]),
        "llm_issue_tags": "|".join(issue_tags),
        "llm_reason": reason,
        "prompt_version": prompt_version,
    }


def save_output(rows: List[Dict[str, object]], path: Path) -> None:
    df = pd.DataFrame(rows)
    if not df.empty:
        df["review_id"] = df["review_id"].fillna("").astype(str)
        df["row_key"] = df["row_key"].fillna("").astype(str)
        df = df.sort_values(["official_scenic_id", "review_id"], kind="mergesort")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def add_binary_tag_columns(df: pd.DataFrame, label_order: List[str]) -> pd.DataFrame:
    tagged = df.copy()
    tag_lists = tagged["llm_issue_tags"].fillna("").map(split_issue_tags)
    tagged["issue_tag_count"] = tag_lists.map(len)
    tagged["issue_flag"] = tagged["issue_tag_count"].gt(0).astype(int)
    for label in label_order:
        tagged[f"tag_{label}"] = tag_lists.map(lambda tags, label=label: int(label in tags))
    return tagged


def build_review_sample(df: pd.DataFrame, sample_size: int) -> pd.DataFrame:
    review_df = df.copy()
    review_df["text_len"] = review_df["review_text"].fillna("").astype(str).str.len()
    review_df["issue_tag_count"] = review_df["llm_issue_tags"].fillna("").map(lambda text: len(split_issue_tags(text)))
    review_df["priority_score"] = (
        review_df["issue_tag_count"].gt(0).astype(int) * 30
        + review_df["issue_tag_count"].ge(2).astype(int) * 15
        + review_df["text_len"].ge(80).astype(int) * 8
        + review_df["text_len"].ge(140).astype(int) * 6
        + review_df["rating"].fillna(5).lt(5).astype(int) * 6
    )
    selected = review_df.sort_values(
        ["priority_score", "issue_tag_count", "text_len", "review_id"],
        ascending=[False, False, False, True],
        kind="mergesort",
    ).head(sample_size)
    return selected[
        [
            "row_key",
            "review_id",
            "official_scenic_id",
            "scenic_name",
            "review_time",
            "rating",
            "review_text",
            "llm_issue_tags",
            "llm_reason",
            "prompt_version",
        ]
    ].copy()


def build_overall_summary(df: pd.DataFrame, label_order: List[str]) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    total_n = len(df)
    tagged_n = int(df["issue_flag"].sum()) if total_n else 0
    for label in label_order:
        col = f"tag_{label}"
        label_n = int(df[col].sum()) if col in df.columns else 0
        rows.append(
            {
                "label": label,
                "label_n": label_n,
                "label_share_all_reviews": round(label_n / total_n, 6) if total_n else 0.0,
                "label_share_issue_reviews": round(label_n / tagged_n, 6) if tagged_n else 0.0,
            }
        )
    return pd.DataFrame(rows)


def build_scenic_summary(df: pd.DataFrame, label_order: List[str]) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    scenic_totals = df.groupby(["official_scenic_id", "scenic_name"], as_index=False).size().rename(columns={"size": "review_n"})
    for _, scenic_row in scenic_totals.iterrows():
        subset = df.loc[df["official_scenic_id"].eq(scenic_row["official_scenic_id"])].copy()
        base = {
            "official_scenic_id": scenic_row["official_scenic_id"],
            "scenic_name": scenic_row["scenic_name"],
            "review_n": int(scenic_row["review_n"]),
            "issue_review_n": int(subset["issue_flag"].sum()),
            "issue_review_share": round(float(subset["issue_flag"].mean()), 6),
        }
        for label in label_order:
            col = f"tag_{label}"
            base[f"{label}_n"] = int(subset[col].sum())
            base[f"{label}_share"] = round(float(subset[col].mean()), 6)
        rows.append(base)
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()

    raw_df = pd.read_csv(args.input_csv, encoding="utf-8-sig")
    prepared_df = prepare_input_table(raw_df)
    args.prepared_input_csv.parent.mkdir(parents=True, exist_ok=True)
    prepared_df.to_csv(args.prepared_input_csv, index=False, encoding="utf-8-sig")

    if args.offset > 0:
        prepared_df = prepared_df.iloc[args.offset :].copy()
    if args.limit > 0:
        prepared_df = prepared_df.head(args.limit).copy()

    if args.prepare_only:
        print(f"prepared_rows={len(prepared_df)}")
        print(f"prepared_input_csv={args.prepared_input_csv}")
        return

    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        raise EnvironmentError(f"Missing API key environment variable: {args.api_key_env}")

    label_data = load_labels(args.label_yaml)
    label_order = list(label_data["label_order"])
    template_text = load_text(args.prompt_template)
    fewshot_text = load_text(args.fewshot_md)

    existing_rows: List[Dict[str, object]] = []
    completed_ids: set[str] = set()
    if args.resume and args.output_csv.exists():
        existing_df = pd.read_csv(args.output_csv, encoding="utf-8-sig")
        existing_df["row_key"] = existing_df["row_key"].fillna("").astype(str)
        existing_rows = existing_df.to_dict("records")
        completed_ids = set(existing_df["row_key"])

    pending_df = prepared_df[~prepared_df["row_key"].astype(str).isin(completed_ids)].copy()
    prompts = {
        str(row["row_key"]): build_prompt(template_text, fewshot_text, label_data, row)
        for _, row in pending_df.iterrows()
    }

    results: Dict[str, Dict[str, object]] = {str(row["row_key"]): row for row in existing_rows}

    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as executor:
        future_map = {}
        for _, row in pending_df.iterrows():
            row_key = str(row["row_key"])
            future = executor.submit(
                label_one_row,
                row=row,
                api_url=args.api_url,
                api_key=api_key,
                model=args.model,
                prompt=prompts[row_key],
                label_order=label_order,
                timeout=args.timeout,
                prompt_version=args.prompt_version,
            )
            future_map[future] = row_key

        for idx, future in enumerate(as_completed(future_map), start=1):
            row_key = future_map[future]
            try:
                results[row_key] = future.result()
            except Exception as exc:  # noqa: BLE001
                matched = prepared_df.loc[prepared_df["row_key"].astype(str) == row_key].iloc[0]
                results[row_key] = {
                    "row_key": row_key,
                    "review_id": matched["review_id"],
                    "official_scenic_id": matched["official_scenic_id"],
                    "scenic_name": matched["scenic_name"],
                    "review_time": matched["review_time"],
                    "rating": matched["rating"],
                    "review_text": sanitize_review_text(matched["review_text"]),
                    "llm_issue_tags": "",
                    "llm_reason": f"ERROR: {type(exc).__name__}: {exc}",
                    "prompt_version": args.prompt_version,
                }
            if idx % 10 == 0 or idx == len(future_map):
                save_output(list(results.values()), args.output_csv)

    output_df = pd.DataFrame(results.values())
    if not output_df.empty:
        output_df["row_key"] = output_df["row_key"].fillna("").astype(str)
        output_df["review_id"] = output_df["review_id"].fillna("").astype(str)
        output_df = output_df.sort_values(["official_scenic_id", "review_id"], kind="mergesort")

    output_df = add_binary_tag_columns(output_df, label_order)
    output_df.to_csv(args.output_csv, index=False, encoding="utf-8-sig")

    merged_df = prepared_df.merge(output_df, on="row_key", how="left", suffixes=("", "_llm"))
    merged_df.to_csv(args.merged_output_csv, index=False, encoding="utf-8-sig")

    review_sample_df = build_review_sample(output_df, sample_size=args.review_sample_size)
    review_sample_df.to_csv(args.review_sample_csv, index=False, encoding="utf-8-sig")

    overall_summary_df = build_overall_summary(output_df, label_order)
    overall_summary_df.to_csv(args.overall_summary_csv, index=False, encoding="utf-8-sig")

    scenic_summary_df = build_scenic_summary(output_df, label_order)
    scenic_summary_df.to_csv(args.scenic_summary_csv, index=False, encoding="utf-8-sig")

    error_rows = int(output_df["llm_reason"].fillna("").astype(str).str.startswith("ERROR:").sum())
    print(f"prepared_rows={len(prepared_df)}")
    print(f"output_rows={len(output_df)}")
    print(f"error_rows={error_rows}")
    print(f"output_csv={args.output_csv}")
    print(f"merged_output_csv={args.merged_output_csv}")
    print(f"review_sample_csv={args.review_sample_csv}")
    print(f"overall_summary_csv={args.overall_summary_csv}")
    print(f"scenic_summary_csv={args.scenic_summary_csv}")


if __name__ == "__main__":
    main()
