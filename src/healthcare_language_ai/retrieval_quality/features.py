"""Controlled retrieval-quality features for Milestone 7."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, cast

from healthcare_language_ai.retrieval.tokenisation import tokens
from healthcare_language_ai.retrieval_quality.contracts import QueryExpansionRule

QUERY_EXPANSION_VERSION = "1.0.0"
NEGATION_FEATURE_VERSION = "1.0.0"
NUMERIC_FEATURE_VERSION = "1.0.0"
ABBREVIATION_VERSION = "1.0.0"
SECTION_ALIAS_VERSION = "1.0.0"

SYNONYM_MAP = {
    "heart": ["cardiac"],
    "scan": ["imaging"],
    "breathing": ["respiratory"],
    "blood": ["haematology"],
    "kidney": ["renal"],
    "liver": ["hepatic"],
    "summary": ["impression"],
    "background": ["history"],
    "observed": ["findings"],
    "review": ["assessment"],
}

ABBREVIATIONS = {
    "ct": {"expansion": "computed tomography", "ambiguous": False},
    "mri": {"expansion": "magnetic resonance imaging", "ambiguous": False},
    "bp": {"expansion": "blood pressure", "ambiguous": False},
    "hr": {"expansion": "heart rate", "ambiguous": False},
    "ms": {"expansion": "ambiguous", "ambiguous": True},
}

SECTION_ALIASES = {
    "history": ["relevant history", "background"],
    "impression": ["summary impression", "interpretive summary"],
    "findings": ["observed findings", "report findings"],
    "plan": ["administrative next step", "workflow note"],
}

NEGATION_MARKERS = ["no", "not", "without", "denies", "negative for", "absence of"]
NUMERIC_PATTERN = re.compile(
    r"(?P<number>\d+(?:\.\d+)?)(?:\s?(?P<unit>mm|cm|kg|mg|ml|bpm|percent|%))?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NegationFeature:
    term: str
    polarity: Literal["affirmed", "negated"]
    version: str = NEGATION_FEATURE_VERSION


@dataclass(frozen=True)
class NumericFeature:
    value: float
    unit: str
    raw: str
    version: str = NUMERIC_FEATURE_VERSION


def expand_query_text(
    text: str,
    *,
    include_synonyms: bool = True,
    include_abbreviations: bool = True,
    include_section_aliases: bool = True,
) -> tuple[str, list[QueryExpansionRule]]:
    lower_tokens = tokens(text)
    expansions: list[QueryExpansionRule] = []
    extra_terms: list[str] = []
    for term in lower_tokens:
        if include_synonyms:
            for expanded in SYNONYM_MAP.get(term, []):
                expansions.append(
                    QueryExpansionRule(
                        expansion_rule_id=f"synonym:{term}:{expanded}",
                        original_term=term,
                        expanded_term=expanded,
                        expansion_type="controlled_synonym",
                        version=QUERY_EXPANSION_VERSION,
                    )
                )
                extra_terms.append(expanded)
        if include_abbreviations and term in ABBREVIATIONS and not ABBREVIATIONS[term]["ambiguous"]:
            expanded = cast(str, ABBREVIATIONS[term]["expansion"])
            expansions.append(
                QueryExpansionRule(
                    expansion_rule_id=f"abbreviation:{term}",
                    original_term=term,
                    expanded_term=expanded,
                    expansion_type="abbreviation",
                    version=QUERY_EXPANSION_VERSION,
                )
            )
            extra_terms.append(expanded)
        if include_section_aliases:
            for expanded in SECTION_ALIASES.get(term, []):
                expansions.append(
                    QueryExpansionRule(
                        expansion_rule_id=f"section_alias:{term}:{expanded}",
                        original_term=term,
                        expanded_term=expanded,
                        expansion_type="section_alias",
                        version=QUERY_EXPANSION_VERSION,
                    )
                )
                extra_terms.append(expanded)
    expanded_text = " ".join([text, *extra_terms]).strip()
    return expanded_text, expansions


def negation_features(text: str, *, window: int = 5) -> list[NegationFeature]:
    text_tokens = tokens(text)
    features: list[NegationFeature] = []
    for index, term in enumerate(text_tokens):
        if term in {"no", "not", "without", "denies"}:
            for scoped in text_tokens[index + 1 : index + 1 + window]:
                features.append(NegationFeature(term=scoped, polarity="negated"))
        elif term not in {"negative", "for", "absence", "of"}:
            features.append(NegationFeature(term=term, polarity="affirmed"))
    lower = text.casefold()
    for phrase in ("negative for", "absence of"):
        if phrase in lower:
            after = lower.split(phrase, 1)[1]
            for scoped in tokens(after)[:window]:
                features.append(NegationFeature(term=scoped, polarity="negated"))
    deduped: dict[tuple[str, str], NegationFeature] = {}
    for feature in features:
        deduped[(feature.term, feature.polarity)] = feature
    return list(deduped.values())


def numeric_features(text: str) -> list[NumericFeature]:
    features: list[NumericFeature] = []
    for match in NUMERIC_PATTERN.finditer(text):
        unit = (match.group("unit") or "number").casefold().replace("%", "percent")
        features.append(
            NumericFeature(value=float(match.group("number")), unit=unit, raw=match.group(0))
        )
    return features


def negation_compatibility(query: str, candidate: str) -> float:
    query_negated = {(f.term, f.polarity) for f in negation_features(query)}
    candidate_negated = {(f.term, f.polarity) for f in negation_features(candidate)}
    penalty = 0.0
    for term, polarity in query_negated:
        opposite = "negated" if polarity == "affirmed" else "affirmed"
        if (term, opposite) in candidate_negated:
            penalty += 0.25
    return max(0.0, 1.0 - penalty)


def numeric_compatibility(query: str, candidate: str) -> float:
    query_numbers = numeric_features(query)
    if not query_numbers:
        return 1.0
    candidate_numbers = numeric_features(candidate)
    if not candidate_numbers:
        return 0.5
    score = 0.0
    for qnum in query_numbers:
        for cnum in candidate_numbers:
            if qnum.value == cnum.value and qnum.unit == cnum.unit:
                score = max(score, 1.0)
            elif qnum.value == cnum.value:
                score = max(score, 0.8)
            elif qnum.unit == cnum.unit:
                score = max(score, 0.4)
    return score
