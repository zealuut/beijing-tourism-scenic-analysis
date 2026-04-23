#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
from snownlp.sentiment import Sentiment, data_path as DEFAULT_SENTIMENT_MODEL_PATH


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_DIR / "data" / "issue_labels" / "experiment4_llm_issue_output_merged.csv"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "data" / "sentiment"
DEFAULT_MANUAL_SEED_PATH = PROJECT_DIR.parent / "ctrip-comment-spider" / "data" / "interim" / "text_gold_seed_24.csv"

MIN_TEXT_LEN = 6
RANDOM_STATE = 42
VALID_CLASSES = ["positive", "neutral", "negative"]
CLASS_INDEX_MAP = {"positive": 1.0, "neutral": 0.5, "negative": 0.0}

THRESHOLD_SCHEMES: Dict[str, Tuple[float, float]] = {
    "scheme_a_pos_ge_0.60_neg_le_0.40": (0.60, 0.40),
    "scheme_b_pos_ge_0.65_neg_le_0.35": (0.65, 0.35),
    "scheme_c_pos_ge_0.70_neg_le_0.30": (0.70, 0.30),
    "scheme_d_pos_ge_0.75_neg_le_0.25": (0.75, 0.25),
    "scheme_e_pos_ge_0.80_neg_le_0.20": (0.80, 0.20),
    "scheme_f_pos_ge_0.80_neg_le_0.15": (0.80, 0.15),
    "scheme_g_pos_ge_0.85_neg_le_0.15": (0.85, 0.15),
    "scheme_h_pos_ge_0.85_neg_le_0.10": (0.85, 0.10),
}


@dataclass
class ThresholdResult:
    scheme_name: str
    pos_threshold: float
    neg_threshold: float
    pseudo_accuracy: float
    pseudo_macro_f1: float
    manual_accuracy: float
    positive_share: float
    neutral_share: float
    negative_share: float
    high_rating_negative_rate: float
    high_rating_no_issue_negative_rate: float
    five_star_no_issue_negative_rate: float
    low_rating_negative_rate: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SnowNLP scenic-domain sentiment scoring.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manual-seed-csv", type=Path, default=DEFAULT_MANUAL_SEED_PATH)
    return parser.parse_args()


def sanitize_text(text: object) -> str:
    return " ".join(str(text or "").split())


def load_input(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig").copy()
    df["review_text"] = df["review_text"].fillna("").astype(str).map(sanitize_text)
    df["text_len"] = df["review_text"].str.len()
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["issue_flag"] = pd.to_numeric(df.get("issue_flag", 0), errors="coerce").fillna(0).astype(int)
    df["issue_tag_count"] = pd.to_numeric(df.get("issue_tag_count", 0), errors="coerce").fillna(0).astype(int)
    return df


def build_training_corpora(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    eligible = df.loc[df["text_len"].ge(MIN_TEXT_LEN)].copy()
    pos_pool = eligible.loc[eligible["rating"].eq(5) & eligible["issue_flag"].eq(0)].copy()
    neg_pool = eligible.loc[(eligible["rating"].le(2)) | ((eligible["rating"].eq(3)) & eligible["issue_flag"].eq(1))].copy()

    if pos_pool.empty or neg_pool.empty:
        raise ValueError("Unable to build SnowNLP training corpora from the current dataset.")

    sample_n = min(len(pos_pool), len(neg_pool))
    pos_sample = pos_pool.sample(n=sample_n, random_state=RANDOM_STATE).sort_values("row_key", kind="mergesort")
    neg_sample = neg_pool.sample(n=sample_n, random_state=RANDOM_STATE).sort_values("row_key", kind="mergesort")
    return pos_sample, neg_sample


def write_corpus(lines: Iterable[str], path: Path) -> None:
    cleaned = [sanitize_text(line) for line in lines if sanitize_text(line)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(cleaned) + "\n", encoding="utf-8")


def train_domain_model(pos_df: pd.DataFrame, neg_df: pd.DataFrame, model_path: Path) -> Sentiment:
    classifier = Sentiment()
    classifier.train(
        [sanitize_text(text) for text in neg_df["review_text"].tolist()],
        [sanitize_text(text) for text in pos_df["review_text"].tolist()],
    )
    classifier.save(str(model_path), iszip=True)
    loaded = Sentiment()
    loaded.load(str(model_path), iszip=True)
    return loaded


def load_default_model() -> Sentiment:
    classifier = Sentiment()
    classifier.load(DEFAULT_SENTIMENT_MODEL_PATH, iszip=True)
    return classifier


def score_texts(classifier: Sentiment, texts: Iterable[str]) -> List[float]:
    scores: List[float] = []
    for text in texts:
        cleaned = sanitize_text(text)
        if not cleaned:
            scores.append(0.5)
            continue
        try:
            score = float(classifier.classify(cleaned))
        except Exception:  # noqa: BLE001
            score = 0.5
        scores.append(max(0.0, min(1.0, score)))
    return scores


def classify_by_threshold(score_01: pd.Series, pos_threshold: float, neg_threshold: float) -> pd.Series:
    classes = pd.Series("neutral", index=score_01.index, dtype="object")
    classes.loc[score_01 >= pos_threshold] = "positive"
    classes.loc[score_01 <= neg_threshold] = "negative"
    return classes


def build_pseudo_gold(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["pseudo_sentiment_class"] = ""
    result.loc[result["rating"].eq(5) & result["issue_flag"].eq(0), "pseudo_sentiment_class"] = "positive"
    result.loc[(result["rating"].le(2)) | ((result["rating"].eq(3)) & result["issue_flag"].eq(1)), "pseudo_sentiment_class"] = "negative"
    result.loc[((result["rating"].eq(3)) & result["issue_flag"].eq(0)) | ((result["rating"].eq(4)) & result["issue_flag"].eq(1)), "pseudo_sentiment_class"] = "neutral"
    return result.loc[result["pseudo_sentiment_class"].isin(VALID_CLASSES)].copy()


def accuracy_score(actual: pd.Series, predicted: pd.Series) -> float:
    if len(actual) == 0:
        return float("nan")
    return float((actual.astype(str) == predicted.astype(str)).mean())


def f1_for_label(actual: pd.Series, predicted: pd.Series, label: str) -> float:
    actual_pos = actual.astype(str).eq(label)
    pred_pos = predicted.astype(str).eq(label)
    tp = int((actual_pos & pred_pos).sum())
    fp = int((~actual_pos & pred_pos).sum())
    fn = int((actual_pos & ~pred_pos).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def macro_f1(actual: pd.Series, predicted: pd.Series) -> float:
    return float(np.mean([f1_for_label(actual, predicted, label) for label in VALID_CLASSES]))


def masked_rate(mask: pd.Series, event: pd.Series) -> float:
    valid_mask = mask.fillna(False)
    if int(valid_mask.sum()) == 0:
        return float("nan")
    return float(event.loc[valid_mask].mean())


def score_manual_seed(manual_df: pd.DataFrame, classifier: Sentiment) -> pd.DataFrame:
    scored = manual_df.copy()
    scored["snownlp_domain_score"] = score_texts(classifier, scored["review_text"].tolist())
    return scored


def choose_recommended_scheme(compare_df: pd.DataFrame) -> str:
    max_macro_f1 = float(compare_df["pseudo_macro_f1"].max())
    selection_df = compare_df.loc[
        compare_df["pseudo_macro_f1"].ge(max_macro_f1 - 0.07) & compare_df["low_rating_negative_rate"].ge(0.95)
    ].copy()
    if selection_df.empty:
        selection_df = compare_df.copy()
    selection_df = selection_df.sort_values(
        [
            "five_star_no_issue_negative_rate",
            "high_rating_no_issue_negative_rate",
            "manual_accuracy",
            "pseudo_macro_f1",
            "pseudo_accuracy",
        ],
        ascending=[True, True, False, False, False],
        kind="mergesort",
    )
    return str(selection_df.iloc[0]["scheme_name"])


def evaluate_thresholds(
    scored_df: pd.DataFrame,
    classifier: Sentiment,
    manual_seed_path: Path,
) -> Tuple[pd.DataFrame, str]:
    pseudo_gold = build_pseudo_gold(scored_df)
    manual_df = None
    if manual_seed_path.exists():
        manual_df = pd.read_csv(manual_seed_path, encoding="utf-8-sig").copy()
        manual_df["review_text"] = manual_df["review_text"].fillna("").astype(str).map(sanitize_text)
        manual_df["manual_sentiment_class"] = manual_df["manual_sentiment_class"].fillna("").astype(str).str.strip().str.lower()
        manual_df = manual_df.loc[manual_df["manual_sentiment_class"].isin(VALID_CLASSES)].copy()
        if not manual_df.empty:
            manual_df = score_manual_seed(manual_df, classifier)

    rows: List[ThresholdResult] = []
    for scheme_name, (pos_threshold, neg_threshold) in THRESHOLD_SCHEMES.items():
        predicted = classify_by_threshold(scored_df["snownlp_domain_score"], pos_threshold, neg_threshold)
        pseudo_pred = classify_by_threshold(pseudo_gold["snownlp_domain_score"], pos_threshold, neg_threshold)
        manual_acc = float("nan")
        if manual_df is not None and not manual_df.empty:
            manual_pred = classify_by_threshold(manual_df["snownlp_domain_score"], pos_threshold, neg_threshold)
            manual_acc = accuracy_score(manual_df["manual_sentiment_class"], manual_pred)

        dist = predicted.value_counts(normalize=True, dropna=False).to_dict()
        negative_event = predicted.eq("negative")
        rows.append(
            ThresholdResult(
                scheme_name=scheme_name,
                pos_threshold=pos_threshold,
                neg_threshold=neg_threshold,
                pseudo_accuracy=accuracy_score(pseudo_gold["pseudo_sentiment_class"], pseudo_pred),
                pseudo_macro_f1=macro_f1(pseudo_gold["pseudo_sentiment_class"], pseudo_pred),
                manual_accuracy=manual_acc,
                positive_share=float(dist.get("positive", 0.0)),
                neutral_share=float(dist.get("neutral", 0.0)),
                negative_share=float(dist.get("negative", 0.0)),
                high_rating_negative_rate=masked_rate(scored_df["rating"].ge(4), negative_event),
                high_rating_no_issue_negative_rate=masked_rate(
                    scored_df["rating"].ge(4) & scored_df["issue_flag"].eq(0),
                    negative_event,
                ),
                five_star_no_issue_negative_rate=masked_rate(
                    scored_df["rating"].eq(5) & scored_df["issue_flag"].eq(0),
                    negative_event,
                ),
                low_rating_negative_rate=masked_rate(scored_df["rating"].le(2), negative_event),
            )
        )

    compare_df = pd.DataFrame([row.__dict__ for row in rows])
    recommended_scheme = choose_recommended_scheme(compare_df)
    compare_df["is_recommended"] = compare_df["scheme_name"].eq(recommended_scheme).astype(int)
    compare_df = compare_df.sort_values(
        [
            "is_recommended",
            "five_star_no_issue_negative_rate",
            "high_rating_no_issue_negative_rate",
            "pseudo_macro_f1",
            "pseudo_accuracy",
        ],
        ascending=[False, True, True, False, False],
        kind="mergesort",
    )
    return compare_df, recommended_scheme


def build_overall_summary(df: pd.DataFrame) -> pd.DataFrame:
    negative_event = df["sentiment_class"].eq("negative")
    return pd.DataFrame(
        [
            {
                "review_n": len(df),
                "avg_default_score": float(df["snownlp_default_score"].mean()),
                "avg_domain_score": float(df["snownlp_domain_score"].mean()),
                "positive_share": float((df["sentiment_class"] == "positive").mean()),
                "neutral_share": float((df["sentiment_class"] == "neutral").mean()),
                "negative_share": float((df["sentiment_class"] == "negative").mean()),
                "avg_sentiment_index": float(df["sentiment_class"].map(CLASS_INDEX_MAP).mean()),
                "high_rating_negative_rate": masked_rate(df["rating"].ge(4), negative_event),
                "high_rating_no_issue_negative_rate": masked_rate(
                    df["rating"].ge(4) & df["issue_flag"].eq(0),
                    negative_event,
                ),
                "five_star_no_issue_negative_rate": masked_rate(
                    df["rating"].eq(5) & df["issue_flag"].eq(0),
                    negative_event,
                ),
                "low_rating_negative_rate": masked_rate(df["rating"].le(2), negative_event),
            }
        ]
    )


def build_scenic_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    grouped = df.groupby(["official_scenic_id", "scenic_name"], as_index=False, sort=True)
    for scenic_id, scenic_name in grouped[["official_scenic_id", "scenic_name"]].first().itertuples(index=False, name=None):
        group = df.loc[(df["official_scenic_id"] == scenic_id) & (df["scenic_name"] == scenic_name)].copy()
        negative_event = group["sentiment_class"].eq("negative")
        rows.append(
            {
                "official_scenic_id": scenic_id,
                "scenic_name": scenic_name,
                "review_n": len(group),
                "avg_rating": float(group["rating"].mean()),
                "avg_default_score": float(group["snownlp_default_score"].mean()),
                "avg_domain_score": float(group["snownlp_domain_score"].mean()),
                "positive_share": float((group["sentiment_class"] == "positive").mean()),
                "neutral_share": float((group["sentiment_class"] == "neutral").mean()),
                "negative_share": float((group["sentiment_class"] == "negative").mean()),
                "avg_sentiment_index": float(group["sentiment_class"].map(CLASS_INDEX_MAP).mean()),
                "high_rating_negative_rate": masked_rate(group["rating"].ge(4), negative_event),
                "high_rating_no_issue_negative_rate": masked_rate(
                    group["rating"].ge(4) & group["issue_flag"].eq(0),
                    negative_event,
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(["avg_sentiment_index", "negative_share"], ascending=[True, False], kind="mergesort")


def write_markdown_report(
    report_path: Path,
    pos_train_n: int,
    neg_train_n: int,
    threshold_compare: pd.DataFrame,
    recommended_scheme: str,
    overall_summary: pd.DataFrame,
) -> None:
    lines: List[str] = []
    lines.append("# Experiment 5 SnowNLP Scenic Sentiment Report")
    lines.append("")
    lines.append("## 1. Method")
    lines.append("- This experiment does not simply replace a sentiment lexicon.")
    lines.append("- SnowNLP is retrained with scenic-domain review text from the current 6000-review project corpus.")
    lines.append("- The domain score is then mapped into `positive / neutral / negative` with calibrated thresholds.")
    lines.append("")
    lines.append("## 2. Training Corpus")
    lines.append(f"- Positive training reviews: {pos_train_n}")
    lines.append(f"- Negative training reviews: {neg_train_n}")
    lines.append("")
    lines.append("## 3. Threshold Comparison")
    lines.append(threshold_compare.to_string(index=False))
    lines.append("")
    lines.append("## 4. Recommended Scheme")
    lines.append(f"- Recommended threshold scheme: `{recommended_scheme}`")
    lines.append("- Selection principle: keep low-rating reviews negative, while reducing false negatives among high-rating no-issue reviews.")
    lines.append("")
    lines.append("## 5. Overall Summary")
    lines.append(overall_summary.to_string(index=False))
    lines.append("")
    lines.append("## 6. Interpretation")
    lines.append("- `snownlp_domain_score` closer to `1` means more positive; closer to `0` means more negative.")
    lines.append("- `neutral` means the emotional polarity is mixed or not strong enough.")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    scored_path = output_dir / "experiment5_snownlp_scored.csv"
    threshold_compare_path = output_dir / "experiment5_snownlp_threshold_compare.csv"
    overall_summary_path = output_dir / "experiment5_snownlp_overall_summary.csv"
    scenic_summary_path = output_dir / "experiment5_snownlp_scenic_summary.csv"
    pos_corpus_path = output_dir / "experiment5_snownlp_pos_corpus.txt"
    neg_corpus_path = output_dir / "experiment5_snownlp_neg_corpus.txt"
    model_path = output_dir / "snownlp_scenic_sentiment.marshal"
    report_path = output_dir / "experiment5_snownlp_report.md"

    df = load_input(args.input_csv.resolve())
    pos_train_df, neg_train_df = build_training_corpora(df)

    write_corpus(pos_train_df["review_text"].tolist(), pos_corpus_path)
    write_corpus(neg_train_df["review_text"].tolist(), neg_corpus_path)

    default_classifier = load_default_model()
    domain_classifier = train_domain_model(pos_train_df, neg_train_df, model_path)

    result_df = df.copy()
    result_df["snownlp_default_score"] = score_texts(default_classifier, result_df["review_text"].tolist())
    result_df["snownlp_domain_score"] = score_texts(domain_classifier, result_df["review_text"].tolist())

    threshold_compare_df, recommended_scheme = evaluate_thresholds(
        scored_df=result_df,
        classifier=domain_classifier,
        manual_seed_path=args.manual_seed_csv.resolve(),
    )
    pos_threshold, neg_threshold = THRESHOLD_SCHEMES[recommended_scheme]
    result_df["sentiment_score"] = result_df["snownlp_domain_score"]
    result_df["sentiment_class"] = classify_by_threshold(result_df["sentiment_score"], pos_threshold, neg_threshold)
    result_df["sentiment_index"] = result_df["sentiment_class"].map(CLASS_INDEX_MAP)
    result_df["sentiment_scheme_name"] = recommended_scheme
    result_df["sentiment_pos_threshold"] = pos_threshold
    result_df["sentiment_neg_threshold"] = neg_threshold

    overall_summary_df = build_overall_summary(result_df)
    scenic_summary_df = build_scenic_summary(result_df)

    result_df.to_csv(scored_path, index=False, encoding="utf-8-sig")
    threshold_compare_df.to_csv(threshold_compare_path, index=False, encoding="utf-8-sig")
    overall_summary_df.to_csv(overall_summary_path, index=False, encoding="utf-8-sig")
    scenic_summary_df.to_csv(scenic_summary_path, index=False, encoding="utf-8-sig")
    write_markdown_report(
        report_path=report_path,
        pos_train_n=len(pos_train_df),
        neg_train_n=len(neg_train_df),
        threshold_compare=threshold_compare_df,
        recommended_scheme=recommended_scheme,
        overall_summary=overall_summary_df,
    )

    print(f"input_rows={len(df)}")
    print(f"pos_train_n={len(pos_train_df)}")
    print(f"neg_train_n={len(neg_train_df)}")
    print(f"recommended_scheme={recommended_scheme}")
    print(f"scored_csv={scored_path}")
    print(f"threshold_compare_csv={threshold_compare_path}")
    print(f"overall_summary_csv={overall_summary_path}")
    print(f"scenic_summary_csv={scenic_summary_path}")
    print(f"report_md={report_path}")


if __name__ == "__main__":
    main()
