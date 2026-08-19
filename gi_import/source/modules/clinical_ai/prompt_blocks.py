"""Reusable prompt blocks — infrastructure scaffolding only (no medical content)."""

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
            text = text.replace(f"{{{{{key}}}}}", str(value))
        return text


def system_role_block() -> PromptBlock:
    return PromptBlock(
        block_id="system_role",
        category="system",
        content="You are a clinical AI assistant operating within a governed healthcare platform.",
    )


def task_instruction_block(prompt_type: str) -> PromptBlock:
    return PromptBlock(
        block_id="task_instruction",
        category="task",
        content=f"Task category: {prompt_type}. Respond using the requested output structure only.",
        metadata={"prompt_type": prompt_type},
    )


def context_block(context_payload: dict[str, Any]) -> PromptBlock:
    lines = ["Structured context:"]
    for source, data in context_payload.items():
        lines.append(f"- {source}: {len(data) if isinstance(data, list) else 'present'}")
    return PromptBlock(
        block_id="context_summary",
        category="context",
        content="\n".join(lines),
        metadata={"sources": list(context_payload.keys())},
    )


def output_format_block() -> PromptBlock:
    return PromptBlock(
        block_id="output_format",
        category="format",
        content=(
            "Use clearly labelled sections when applicable: NARRATIVE, BULLETS, TABLE, "
            "RECOMMENDATIONS, REFERENCES."
        ),
    )


def safety_guardrail_block() -> PromptBlock:
    return PromptBlock(
        block_id="safety_guardrail",
        category="safety",
        content="Do not invent patient data. Use only supplied context.",
    )


BLOCK_REGISTRY: dict[str, callable] = {
    "system_role": system_role_block,
    "task_instruction": task_instruction_block,
    "context": context_block,
    "output_format": output_format_block,
    "safety_guardrail": safety_guardrail_block,
}


def blocks_for_prompt_type(prompt_type: str, context_payload: dict[str, Any]) -> list[PromptBlock]:
    return [
        system_role_block(),
        safety_guardrail_block(),
        task_instruction_block(prompt_type),
        context_block(context_payload),
        output_format_block(),
    ]
