"""
Secondary Field Indexing Module.
Allows indexing and fast lookup on key-value record field metadata.
"""

import json
import os
from typing import Dict, Set, List, Any, Optional


class SecondaryIndex:
    """
    Maintains inverted maps from field:value pairs to matching primary record keys.
    """

    def __init__(self):
        # Format: { field_name: { field_value_str: { set of record_keys } } }
        self._index: Dict[str, Dict[str, Set[str]]] = {}

    def index_record(self, key: str, fields: Dict[str, Any]):
        """Index a key's fields."""
        if not fields:
            return
        
        for fname, fval in fields.items():
            val_str = str(fval)
            if fname not in self._index:
                self._index[fname] = {}
            if val_str not in self._index[fname]:
                self._index[fname][val_str] = set()
            self._index[fname][val_str].add(key)

    def unindex_record(self, key: str, fields: Optional[Dict[str, Any]] = None):
        """Remove a key from field indexes."""
        if fields:
            for fname, fval in fields.items():
                val_str = str(fval)
                if fname in self._index and val_str in self._index[fname]:
                    self._index[fname][val_str].discard(key)
                    if not self._index[fname][val_str]:
                        del self._index[fname][val_str]
                    if not self._index[fname]:
                        del self._index[fname]
        else:
            # Full scan removal across all indexed fields for this key
            for fname in list(self._index.keys()):
                for val_str in list(self._index[fname].keys()):
                    self._index[fname][val_str].discard(key)
                    if not self._index[fname][val_str]:
                        del self._index[fname][val_str]
                if not self._index[fname]:
                    del self._index[fname]

    def query(self, field_conditions: Dict[str, Any]) -> List[str]:
        """
        Query for keys matching ALL specified field_name=field_value conditions.
        """
        if not field_conditions:
            return []

        matching_sets: List[Set[str]] = []
        for fname, fval in field_conditions.items():
            val_str = str(fval)
            keys_for_cond = self._index.get(fname, {}).get(val_str, set())
            matching_sets.append(keys_for_cond)

        if not matching_sets:
            return []

        # Perform set intersection for AND semantics
        result_set = set.intersection(*matching_sets)
        return sorted(list(result_set))

    def get_stats(self) -> Dict[str, int]:
        """Return counts of indexed fields and total unique values."""
        total_values = sum(len(val_map) for val_map in self._index.values())
        return {
            "indexed_fields": len(self._index),
            "indexed_values": total_values
        }

    def clear(self):
        self._index.clear()

    def serialize(self) -> str:
        """Convert index state into JSON string for snapshots."""
        raw_index = {}
        for fname, val_map in self._index.items():
            raw_index[fname] = {v_str: list(keys) for v_str, keys in val_map.items()}
        return json.dumps(raw_index, indent=2)

    def save_to_file(self, filepath: str):
        """Save index state snapshot to file."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        raw_index = {}
        for fname, val_map in self._index.items():
            raw_index[fname] = {v_str: sorted(list(keys)) for v_str, keys in val_map.items()}
        
        tmp_file = filepath + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(raw_index, f, indent=2)
        os.replace(tmp_file, filepath)

    def load_from_file(self, filepath: str):
        """Load index state from file snapshot."""
        if not os.path.exists(filepath):
            return
        with open(filepath, "r", encoding="utf-8") as f:
            raw_index = json.load(f)
        
        self.clear()
        for fname, val_map in raw_index.items():
            self._index[fname] = {}
            for v_str, keys_list in val_map.items():
                self._index[fname][v_str] = set(keys_list)
