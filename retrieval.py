"""
Mechnari.ai - Semantic Retrieval Agent
=======================================
Answers the cold-start question: an engineer is designing a part that does
not exist yet - no part number, no DFMEA, no warranty history. What has this
company already learned that applies to it?

Route: describe the part in words -> find the closest historical parts by
TF-IDF cosine similarity -> take the failure modes known for the kinds of
part those neighbours are -> rank by severity and warranty evidence.

Three design decisions, each forced by measurement rather than taste
(evaluate_retrieval() reproduces the numbers):

1. THE VECTORISER NEVER SEES THE LABEL. The corpus is built from descriptive
   text only - component name, function, material - never from part type or
   family names. Otherwise type inference would read the answer off the
   feature vector and the accuracy below would be fiction. System package is
   excluded too: it groups parts by circuit, which actively fights grouping
   them by kind, and dropping it moved type accuracy from 26% to 34%.

2. THE HEAD NOUN IS WEIGHTED, AND IT IS THE LAST ONE. In a mechanical BOM
   the head noun of a component name determines its type, but bag-of-words
   drowns that one noun in medium words, so it is weighted up. English
   compound nouns are head-final: a "Fuel Return Line Clamp" is a clamp, not
   a line, so only the LAST component noun in the name counts. Boosting every
   noun in the name instead scored a "Fuel Return Line" as a clamp, and cost
   4 points of mode recall.

   The lexicon below is a vocabulary of component nouns, not a mapping to
   type labels; the model still learns which noun goes with which type from
   the corpus.

3. THE PROPOSAL UNIONS THE NEIGHBOURS' TYPES RATHER THAN PICKING A WINNER.
   Top-1 type prediction tops out near 50% on a 50-part corpus spread over 17
   types, and no amount of tuning fixes that - after holding a part out, some
   types have a single sibling left. Rather than assert a type it cannot
   support, the agent proposes the modes for every kind of part among the
   neighbours: 76% of the modes that truly apply, in about 19 candidates out
   of 71, each carrying its provenance. Winner-take-all scored 57%.

   So this returns a shortlist for an engineer to confirm, not a verdict. The
   leading type is offered as a suggestion with its confidence attached.

TF-IDF is the honest choice at this corpus size. Moving to embeddings means
replacing _document and _vectorise; nothing downstream changes.
"""

from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import data_layer
import risk_engine

DEFAULT_TOP_K = 5

# Below this cosine similarity nothing in the corpus is a useful analogue.
MIN_SIMILARITY = 0.08

# Share of the top-k similarity mass the leading type needs before it is
# offered as more than a guess.
MIN_TYPE_CONFIDENCE = 0.45

NAME_WEIGHT = 2
HEAD_NOUN_WEIGHT = 6

# Component nouns, not type labels. See design decision 2.
HEAD_NOUNS = frozenset([
    "hose", "line", "tube", "tubing", "pipe", "clamp", "strap", "bracket",
    "mount", "plate", "valve", "solenoid", "coupling", "coupler", "connector",
    "fitting", "adapter", "port", "seal", "o-ring", "oring", "boot", "grommet",
    "gasket", "conduit", "sleeve", "cable", "harness", "filter", "strainer",
    "separator", "bowl", "cock", "cap", "core",
])

_CACHE: Dict[str, Any] = {}


def _head_nouns(text: str) -> List[str]:
    """The head noun of a component name: the last one, not every one."""
    words = [w.strip(":,()/").lower() for w in text.split()]
    found = [w for w in words if w in HEAD_NOUNS]
    return found[-1:]


def _document(part_name: str, function: str = "", material: str = "") -> str:
    """Build one corpus document, or a query, in the same shape."""
    name = (part_name or "").lower()
    chunks = [name] * NAME_WEIGHT
    chunks.extend(_head_nouns(name) * HEAD_NOUN_WEIGHT)
    if function:
        chunks.append(function.lower())
    if material:
        chunks.append(material.lower())
    return " ".join(c for c in chunks if c)


def describe(part_name: str, function: str = "", material: str = "") -> str:
    """
    Turn an engineer's description of a new part into a retrieval query.

    System package is deliberately not a parameter: grouping by circuit fights
    grouping by kind of part. Filter by package after retrieval if you need to.
    """
    return _document(part_name, function, material)


def _corpus() -> pd.DataFrame:
    parts = data_layer.parts().copy()
    parts["_text"] = [
        _document(row["item_reference"], row["elementary_function"], row["material_type"])
        for _, row in parts.iterrows()
    ]
    return parts


def _vectorise():
    """Fit the TF-IDF space once per process, over the active BOM."""
    if "matrix" in _CACHE:
        return _CACHE["vectorizer"], _CACHE["matrix"], _CACHE["parts"]

    parts = _corpus()
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2), sublinear_tf=True, stop_words="english", min_df=1)
    matrix = vectorizer.fit_transform(parts["_text"])
    _CACHE.update({"vectorizer": vectorizer, "matrix": matrix, "parts": parts})
    return vectorizer, matrix, parts


def reload():
    """Drop the fitted space - call after regenerating the knowledge base."""
    _CACHE.clear()


def find_similar_parts(description: str, top_k: int = DEFAULT_TOP_K,
                       exclude_part_id: Optional[str] = None) -> pd.DataFrame:
    """
    The historical parts closest to a free-text description, best first.

    exclude_part_id supports leave-one-out evaluation: hide a part and ask
    whether the rest of the corpus still recognises what it is.
    """
    if not description or not description.strip():
        return pd.DataFrame()

    vectorizer, matrix, parts = _vectorise()
    scores = cosine_similarity(vectorizer.transform([description.lower()]), matrix)[0]

    result = parts[["part_id", "item_reference", "system_package", "material_type",
                    "elementary_function", "part_type_id", "part_type_name",
                    "family_id", "family_name"]].copy()
    result["similarity"] = scores.round(4)

    if exclude_part_id is not None:
        result = result[result["part_id"] != exclude_part_id]

    result = result[result["similarity"] > 0]
    return result.sort_values("similarity", ascending=False).head(top_k).reset_index(drop=True)


def infer_part_type(description: str, top_k: int = DEFAULT_TOP_K,
                    exclude_part_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Suggest what kind of part a description refers to, from its neighbours.

    Neighbours vote weighted by similarity. The leading type is a suggestion
    with a confidence attached, never a decision - see design decision 3.
    """
    neighbours = find_similar_parts(description, top_k, exclude_part_id)
    empty = {
        "confident": False,
        "reason": "Nothing in the knowledge base resembles this description.",
        "part_type_id": None, "part_type_name": None,
        "family_id": None, "family_name": None,
        "confidence": 0.0, "best_similarity": 0.0,
        "candidate_types": [], "neighbours": neighbours,
    }
    if neighbours.empty:
        return empty

    best_similarity = float(neighbours["similarity"].iloc[0])
    votes = neighbours.groupby(
        ["part_type_id", "part_type_name", "family_id", "family_name"]
    )["similarity"].sum().sort_values(ascending=False)
    total = float(votes.sum())
    if not total:
        return empty

    winner = votes.index[0]
    confidence = float(votes.iloc[0] / total)
    confident = best_similarity >= MIN_SIMILARITY and confidence >= MIN_TYPE_CONFIDENCE

    if best_similarity < MIN_SIMILARITY:
        reason = ("Closest match scores only %.2f - too weak to rely on. Name the "
                  "part type directly." % best_similarity)
    elif confidence < MIN_TYPE_CONFIDENCE:
        reason = ("The closest parts disagree on the kind of part (%.0f%% for the "
                  "leading type), so modes from every neighbouring type are "
                  "proposed. Confirm the type before relying on them."
                  % (confidence * 100))
    else:
        reason = "%d of the %d closest parts are this kind of part." % (
            int((neighbours["part_type_id"] == winner[0]).sum()), len(neighbours))

    return {
        "confident": confident,
        "reason": reason,
        "part_type_id": winner[0],
        "part_type_name": winner[1],
        "family_id": winner[2],
        "family_name": winner[3],
        "confidence": round(confidence, 3),
        "best_similarity": round(best_similarity, 4),
        "candidate_types": [
            {"part_type_id": idx[0], "part_type_name": idx[1],
             "family_id": idx[2], "family_name": idx[3],
             "weight": round(float(value) / total, 3)}
            for idx, value in votes.items()
        ],
        "neighbours": neighbours,
    }


def candidate_failure_modes(scope_ids: Iterable[str]) -> pd.DataFrame:
    """
    Every failure mode attached to the given type or family scopes, scored.

    Severity comes from the effect registry and Occurrence from the measured
    warranty rate for that mode, so a proposed DFMEA starts from evidence
    rather than a blank sheet. Detection is the baseline control strength for
    the mode - a new part has no controls yet, so this is what it inherits.
    """
    scope_ids = list(dict.fromkeys(s for s in scope_ids if s))
    catalog = data_layer.failure_mode_catalog()
    applicable = catalog[catalog["scope_id"].isin(scope_ids)].copy()
    if applicable.empty:
        return applicable

    merged = applicable.merge(risk_engine.mode_evidence(), on="mode_id", how="left")
    merged["field_reports"] = merged["field_reports"].fillna(0).astype(int)
    merged["field_claims"] = merged["field_claims"].fillna(0).astype(int)
    merged["claims_per_1000"] = merged["claims_per_1000"].fillna(0.0)
    merged["evidence_ids"] = merged["evidence_ids"].fillna("no field record")
    merged["derived_occurrence"] = merged["derived_occurrence"].fillna(1).astype(int)

    merged["severity"] = merged["standard_severity"].astype(int)
    merged["occurrence"] = merged["derived_occurrence"]
    merged["detection"] = merged["baseline_detection"].astype(int)
    merged["action_priority"] = [
        risk_engine.action_priority(s, o, d)
        for s, o, d in zip(merged["severity"], merged["occurrence"], merged["detection"])
    ]
    merged["rpn_legacy"] = [
        risk_engine.rpn(s, o, d)
        for s, o, d in zip(merged["severity"], merged["occurrence"], merged["detection"])
    ]
    merged["learned_from"] = merged["origin_part_name"] + " (" + merged["origin_part_id"] + ")"

    return merged.sort_values(
        by=["severity", "field_claims"], ascending=[False, False]
    ).reset_index(drop=True)


def propose_dfmea(description: str, top_k: int = DEFAULT_TOP_K,
                  part_type_id: Optional[str] = None) -> Dict[str, Any]:
    """
    A grounded DFMEA starting point for a part that does not exist yet.

    Pass part_type_id to override the suggestion once an engineer has
    confirmed the type; the proposal then narrows to that type and its family.

    This is a proposal, not an analysis. It says what the company's own
    history says a part like this should be checked for, and an engineer still
    owns every row.
    """
    inference = infer_part_type(description, top_k)
    if inference["part_type_id"] is None:
        return {
            "status": "no_match", "reason": inference["reason"],
            "inference": inference, "neighbours": inference["neighbours"],
            "candidates": pd.DataFrame(), "scopes_used": [],
            "safety_candidates": 0, "confirmed": False,
        }

    if part_type_id:
        types = data_layer.part_types()
        row = types[types["part_type_id"] == part_type_id]
        if row.empty:
            raise KeyError("Unknown part_type_id: %s" % part_type_id)
        scopes = [part_type_id, row.iloc[0]["family_id"]]
        leading_type_id = part_type_id
        leading_type_name = row.iloc[0]["part_type_name"]
        family_name = row.iloc[0]["family_name"]
        confirmed = True
    else:
        # Union every kind of part among the neighbours - design decision 3.
        scopes = []
        for candidate in inference["candidate_types"]:
            scopes.extend([candidate["part_type_id"], candidate["family_id"]])
        leading_type_id = inference["part_type_id"]
        leading_type_name = inference["part_type_name"]
        family_name = inference["family_name"]
        confirmed = False

    candidates = candidate_failure_modes(scopes)
    return {
        "status": "success",
        "reason": inference["reason"],
        "confident": inference["confident"],
        "confirmed": confirmed,
        "part_type_id": leading_type_id,
        "part_type_name": leading_type_name,
        "family_name": family_name,
        "confidence": inference["confidence"],
        "candidate_types": inference["candidate_types"],
        "neighbours": inference["neighbours"],
        "inference": inference,
        "candidates": candidates,
        "scopes_used": scopes,
        "safety_candidates": int((candidates["severity"] >= 9).sum())
        if not candidates.empty else 0,
    }


# =====================================================================
# VALIDATION
# =====================================================================

def evaluate_retrieval(top_k: int = DEFAULT_TOP_K) -> Dict[str, Any]:
    """
    Leave-one-out evaluation. Each part is hidden in turn, described using
    only its own text, and the remaining 49 are asked what it is.

    Four numbers, because one would be misleading:

      type_top1_accuracy   the leading type is exactly right. Low by nature -
                           17 types over 50 parts, some with one sibling left
                           after the hold-out.
      family_top1_accuracy the leading family is right. What matters more,
                           since family-scoped modes are the general lessons.
      type_recall_at_k     the true type is somewhere among the neighbours,
                           which is what the engineer actually chooses from.
      mode_recall          of the failure modes that truly apply to the held
                           out part, the share the proposal surfaces. This is
                           the product metric - it is what the engineer walks
                           away with.
    """
    parts = _corpus()
    catalog = data_layer.failure_mode_catalog()
    modes_by_scope: Dict[str, set] = {}
    for _, row in catalog.iterrows():
        modes_by_scope.setdefault(row["scope_id"], set()).add(row["mode_id"])

    type_hits = family_hits = recall_hits = abstentions = 0
    mode_recalls: List[float] = []
    proposed_counts: List[int] = []
    misses: List[Dict[str, Any]] = []

    for _, row in parts.iterrows():
        inference = infer_part_type(row["_text"], top_k, exclude_part_id=row["part_id"])

        if inference["family_id"] == row["family_id"]:
            family_hits += 1
        if inference["part_type_id"] == row["part_type_id"]:
            type_hits += 1
        else:
            misses.append({
                "part_id": row["part_id"],
                "component": row["item_reference"],
                "true_type": row["part_type_name"],
                "leading_type": inference["part_type_name"],
                "true_type_offered": any(
                    c["part_type_id"] == row["part_type_id"]
                    for c in inference["candidate_types"]),
                "confidence": inference["confidence"],
            })
        if any(c["part_type_id"] == row["part_type_id"]
               for c in inference["candidate_types"]):
            recall_hits += 1
        if not inference["confident"]:
            abstentions += 1

        truth = modes_by_scope.get(row["part_type_id"], set()) | \
            modes_by_scope.get(row["family_id"], set())
        proposed: set = set()
        for candidate in inference["candidate_types"]:
            proposed |= modes_by_scope.get(candidate["part_type_id"], set())
            proposed |= modes_by_scope.get(candidate["family_id"], set())
        proposed_counts.append(len(proposed))
        if truth:
            mode_recalls.append(len(truth & proposed) / len(truth))

    total = len(parts)
    return {
        "parts_evaluated": total,
        "top_k": top_k,
        "catalog_size": len(catalog),
        "type_top1_accuracy": round(type_hits / total, 3),
        "family_top1_accuracy": round(family_hits / total, 3),
        "type_recall_at_k": round(recall_hits / total, 3),
        "mode_recall": round(sum(mode_recalls) / len(mode_recalls), 3),
        "mean_modes_proposed": round(float(np.mean(proposed_counts)), 1),
        "low_confidence_rate": round(abstentions / total, 3),
        "misses": misses,
    }


if __name__ == "__main__":
    metrics = evaluate_retrieval()
    print("Leave-one-out retrieval evaluation (k=%d, %d parts, %d catalogued modes)"
          % (metrics["top_k"], metrics["parts_evaluated"], metrics["catalog_size"]))
    print("  leading type exactly right : %.0f%%" % (metrics["type_top1_accuracy"] * 100))
    print("  leading family right       : %.0f%%" % (metrics["family_top1_accuracy"] * 100))
    print("  true type among neighbours : %.0f%%" % (metrics["type_recall_at_k"] * 100))
    print("  MODE RECALL (product metric): %.0f%%  in %.1f candidates of %d"
          % (metrics["mode_recall"] * 100, metrics["mean_modes_proposed"],
             metrics["catalog_size"]))
    print("  flagged low confidence     : %.0f%%" % (metrics["low_confidence_rate"] * 100))

    print("\n" + "=" * 78)
    query = describe(
        part_name="New EPDM Fuel Return Line",
        function="Return unburnt diesel from the injector rail to the tank",
        material="EPDM rubber with textile braid",
    )
    proposal = propose_dfmea(query)
    print("Cold start: a part that does not exist yet")
    print("  suggested type : %s (%s, %.0f%% of the vote)" % (
        proposal["part_type_name"],
        "confident" if proposal["confident"] else "needs confirmation",
        proposal["confidence"] * 100))
    print("  %s" % proposal["reason"])
    print("\n  closest historical parts:")
    for _, row in proposal["neighbours"].iterrows():
        print("    %.3f  %-12s %-42.42s [%s]" % (
            row["similarity"], row["part_id"], row["item_reference"],
            row["part_type_name"]))
    print("\n  proposed DFMEA rows (top 8 of %d):" % len(proposal["candidates"]))
    for _, row in proposal["candidates"].head(8).iterrows():
        print("    S=%-2d O=%-2d D=%-2d AP=%-2s %-46.46s" % (
            row["severity"], row["occurrence"], row["detection"],
            row["action_priority"], row["failure_mode"]))
        print("             from %s" % row["learned_from"])
        print("             evidence %s" % row["evidence_ids"])
