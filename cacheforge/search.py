"""
Full-Text Inverted Search Engine.
Implements tokenization, term-frequency inverted index, TF-IDF relevance scoring, and index persistence.
"""

import json
import math
import os
import re
from typing import Dict, List, Tuple, Set, Optional

# Basic stop words list for filtering token noise
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "were", "will", "with"
}


def tokenize(text: str) -> List[str]:
    """
    Tokenize input string into normalized alphanumeric terms.
    Applies lowercasing, punctuation stripping, and basic length filtering.
    """
    if not text:
        return []
    words = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())
    return [w for w in words if w not in STOP_WORDS]


class FullTextSearchEngine:
    """
    Lightweight Inverted Index for Full-Text Search and Relevance Ranking.
    """

    def __init__(self):
        # Format: { token: { record_key: term_frequency_count } }
        self._inverted_index: Dict[str, Dict[str, int]] = {}
        # Tracks total term count per document for TF normalization: { record_key: total_tokens }
        self._doc_lengths: Dict[str, int] = {}
        # Stores keys currently indexed
        self._indexed_keys: Set[str] = set()

    def index_record(self, key: str, text: str):
        """Index or re-index text contents for a record key."""
        # Unindex prior text if re-indexing
        if key in self._indexed_keys:
            self.unindex_record(key)

        tokens = tokenize(text)
        if not tokens:
            return

        self._indexed_keys.add(key)
        self._doc_lengths[key] = len(tokens)

        # Count frequencies
        token_counts: Dict[str, int] = {}
        for token in tokens:
            token_counts[token] = token_counts.get(token, 0) + 1

        for token, count in token_counts.items():
            if token not in self._inverted_index:
                self._inverted_index[token] = {}
            self._inverted_index[token][key] = count

    def unindex_record(self, key: str):
        """Remove a record key from the inverted index."""
        if key not in self._indexed_keys:
            return

        self._indexed_keys.discard(key)
        self._doc_lengths.pop(key, None)

        for token in list(self._inverted_index.keys()):
            if key in self._inverted_index[token]:
                del self._inverted_index[token][key]
                if not self._inverted_index[token]:
                    del self._inverted_index[token]

    def search(self, query: str, active_keys: Optional[Set[str]] = None) -> List[Tuple[str, float]]:
        """
        Search for query terms using TF-IDF document scoring.
        Returns list of (record_key, relevance_score) sorted by highest score first.
        If active_keys is provided, filters out deleted or expired keys.
        """
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        total_docs = len(self._indexed_keys)
        if total_docs == 0:
            return []

        scores: Dict[str, float] = {}

        for token in query_tokens:
            posting = self._inverted_index.get(token, {})
            if not posting:
                continue

            # IDF = log(1 + Total Documents / Document Frequency of Token)
            doc_freq = len(posting)
            idf = math.log(1.0 + (total_docs / doc_freq))

            for key, term_freq in posting.items():
                if active_keys is not None and key not in active_keys:
                    continue

                doc_len = self._doc_lengths.get(key, 1)
                tf = term_freq / doc_len  # Normalized Term Frequency
                score = tf * idf
                scores[key] = scores.get(key, 0.0) + score

        # Sort by score descending, then key ascending
        results = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return results

    def get_stats(self) -> Dict[str, int]:
        """Return search index statistics."""
        return {
            "indexed_documents": len(self._indexed_keys),
            "unique_terms": len(self._inverted_index)
        }

    def clear(self):
        self._inverted_index.clear()
        self._doc_lengths.clear()
        self._indexed_keys.clear()

    def save_to_file(self, filepath: str):
        """Persist inverted search index snapshot to disk."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = {
            "inverted_index": self._inverted_index,
            "doc_lengths": self._doc_lengths,
            "indexed_keys": list(self._indexed_keys)
        }
        tmp_file = filepath + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_file, filepath)

    def load_from_file(self, filepath: str):
        """Restore inverted search index snapshot from disk."""
        if not os.path.exists(filepath):
            return
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._inverted_index = data.get("inverted_index", {})
        self._doc_lengths = data.get("doc_lengths", {})
        self._indexed_keys = set(data.get("indexed_keys", []))
