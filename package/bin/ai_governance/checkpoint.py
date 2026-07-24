"""KV Store checkpoint management for modular inputs (SHC-safe)."""

from __future__ import annotations

from typing import Any, Dict

from solnlib.modular_input import checkpointer

from ai_governance import ADDON_NAME, CHECKPOINT_COLLECTION


class CheckpointStore:
    """Persist input checkpoints in the Splunk KV Store."""

    def __init__(self, session_key, collection_name=CHECKPOINT_COLLECTION):
        self._checkpointer = checkpointer.KVStoreCheckpointer(
            collection_name,
            session_key,
            ADDON_NAME,
        )

    def get(self, input_key: str) -> Dict[str, Any]:
        state = self._checkpointer.get(input_key)
        if isinstance(state, dict):
            return state
        return {}

    def set(self, input_key: str, state: Dict[str, Any]) -> None:
        self._checkpointer.update(input_key, state)

    def update(self, input_key: str, **fields: Any) -> Dict[str, Any]:
        state = self.get(input_key)
        state.update(fields)
        self.set(input_key, state)
        return state
