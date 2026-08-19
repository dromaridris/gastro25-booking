"""Modular prompt generation engine."""

from __future__ import annotations

from typing import Any

from .constants import ALL_PROMPT_TYPES
from .prompt_blocks import PromptBlock, blocks_for_prompt_type


class PromptEngine:
    """
    Assembles prompts from reusable blocks.

    Sprint 9A: architecture only — no medical reasoning content.
    """

    def __init__(self, extra_blocks: dict[str, list[PromptBlock]] | None = None) -> None:
        self._extra_blocks = extra_blocks or {}

    def register_blocks(self, prompt_type: str, blocks: list[PromptBlock]) -> None:
        self._extra_blocks[prompt_type] = blocks

    def supported_prompt_types(self) -> tuple[str, ...]:
        return ALL_PROMPT_TYPES

    def build(
        self,
        prompt_type: str,
        *,
        context_payload: dict[str, Any],
        variables: dict[str, Any] | None = None,
    ) -> str:
        if prompt_type not in ALL_PROMPT_TYPES:
            raise ValueError(f"Unsupported prompt_type: {prompt_type}")

        blocks = blocks_for_prompt_type(prompt_type, context_payload)
        blocks.extend(self._extra_blocks.get(prompt_type, []))

        sections: list[str] = []
        for block in blocks:
            sections.append(block.render(variables))
        return "\n\n".join(sections)

    def build_messages(
        self,
        prompt_type: str,
        *,
        context_payload: dict[str, Any],
        variables: dict[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        """Provider-neutral message list."""
        prompt = self.build(prompt_type, context_payload=context_payload, variables=variables)
        return [
            {"role": "system", "content": "Clinical AI infrastructure session."},
            {"role": "user", "content": prompt},
        ]
