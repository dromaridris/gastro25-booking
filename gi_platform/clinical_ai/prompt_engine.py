"""Modular prompt generation engine."""

from __future__ import annotations

from typing import Any

from gi_platform.clinical_ai.constants import ALL_PROMPT_TYPES
from gi_platform.clinical_ai.prompt_blocks import PromptBlock, blocks_for_prompt_type


class PromptEngine:
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
        user_question: str | None = None,
    ) -> str:
        if prompt_type not in ALL_PROMPT_TYPES:
            raise ValueError(f'Unsupported prompt_type: {prompt_type}')
        blocks = blocks_for_prompt_type(
            prompt_type, context_payload, user_question=user_question,
        )
        blocks.extend(self._extra_blocks.get(prompt_type, []))
        sections = [block.render(variables) for block in blocks]
        return '\n\n'.join(sections)

    def build_messages(
        self,
        prompt_type: str,
        *,
        context_payload: dict[str, Any],
        variables: dict[str, Any] | None = None,
        user_question: str | None = None,
    ) -> list[dict[str, str]]:
        prompt = self.build(
            prompt_type, context_payload=context_payload,
            variables=variables, user_question=user_question,
        )
        return [
            {'role': 'system', 'content': 'Clinical AI infrastructure session.'},
            {'role': 'user', 'content': prompt},
        ]
