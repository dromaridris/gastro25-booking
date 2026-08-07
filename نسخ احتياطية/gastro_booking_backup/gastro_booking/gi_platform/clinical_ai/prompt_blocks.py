"""Prompt blocks — ported from GastroIntelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptBlock:
    block_id: str
    category: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def render(self, variables: dict[str, Any] | None = None) -> str:
        text = self.content
        for key, value in (variables or {}).items():
            text = text.replace(f'{{{{{key}}}}}', str(value))
        return text


def system_role_block() -> PromptBlock:
    return PromptBlock(
        block_id='system_role', category='system',
        content='You are a clinical AI assistant operating within a governed gastroenterology department platform.',
    )


def task_instruction_block(prompt_type: str) -> PromptBlock:
    return PromptBlock(
        block_id='task_instruction', category='task',
        content=f'Task category: {prompt_type}. Respond using the requested output structure only.',
        metadata={'prompt_type': prompt_type},
    )


def context_block(context_payload: dict[str, Any]) -> PromptBlock:
    lines = ['Structured context:']
    for source, data in context_payload.items():
        if isinstance(data, list):
            lines.append(f'- {source}: {len(data)} item(s)')
        elif isinstance(data, dict):
            lines.append(f'- {source}: {len(data)} field(s)')
        else:
            lines.append(f'- {source}: present')
    return PromptBlock(
        block_id='context_summary', category='context',
        content='\n'.join(lines),
        metadata={'sources': list(context_payload.keys())},
    )


def user_question_block(question: str) -> PromptBlock:
    return PromptBlock(
        block_id='user_question', category='user',
        content=f'Clinician question:\n{question}',
    )


def output_format_block() -> PromptBlock:
    return PromptBlock(
        block_id='output_format', category='format',
        content=(
            'Use clearly labelled sections when applicable: NARRATIVE, BULLETS, TABLE, '
            'RECOMMENDATIONS, REFERENCES.'
        ),
    )


def safety_guardrail_block() -> PromptBlock:
    return PromptBlock(
        block_id='safety_guardrail', category='safety',
        content='Do not invent patient data. Use only supplied context.',
    )


def blocks_for_prompt_type(
    prompt_type: str,
    context_payload: dict[str, Any],
    *,
    user_question: str | None = None,
) -> list[PromptBlock]:
    blocks = [
        system_role_block(),
        safety_guardrail_block(),
        task_instruction_block(prompt_type),
        context_block(context_payload),
    ]
    if user_question:
        blocks.append(user_question_block(user_question))
    blocks.append(output_format_block())
    return blocks
