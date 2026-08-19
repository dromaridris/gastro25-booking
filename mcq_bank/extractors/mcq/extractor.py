import re
from mcq_bank.extractors.base import BaseExtractor, ExtractedItem
from mcq_bank.extractors.text_utils import clean_prose
from mcq_bank.extractors.mcq.schema import build_payload
from mcq_bank.extractors.mcq.consistency_check import check_rationale_answer_consistency

OPTION_LINE_RE = re.compile(r"^\s*([A-E])\s?\.\s+(.*)$")


class McqExtractor(BaseExtractor):
    content_type = "mcq"

    # ---------- pattern detection ----------

    def detect_pattern(self, chapter_text: str) -> str:
        if re.search(r"^Question\s+\d+\s*$", chapter_text, re.MULTILINE) and \
           re.search(r"^CORRECT ANSWER:", chapter_text, re.MULTILINE):
            return "type_a_inline_answer"
        if re.search(r"^\s*QUESTIONS\s*$", chapter_text, re.MULTILINE | re.IGNORECASE) and \
           re.search(r"^\s*ANSWERS\s*$", chapter_text, re.MULTILINE | re.IGNORECASE):
            return "type_b_answer_key_section"
        return "unknown"

    def extract(self, chapter_text: str) -> list:
        pattern = self.detect_pattern(chapter_text)
        if pattern == "type_a_inline_answer":
            return self._extract_type_a(chapter_text)
        if pattern == "type_b_answer_key_section":
            return self._extract_type_b(chapter_text)
        return []

    # ---------- Type A: "Question N" ... "CORRECT ANSWER: X" ... "RATIONALE" ... "REFERENCES" ----------

    def _extract_type_a(self, chapter_text: str) -> list:
        lines = chapter_text.split("\n")
        q_starts = []
        for i, line in enumerate(lines):
            m = re.match(r"^Question (\d+)\s*$", line.strip())
            if m:
                q_starts.append((i, int(m.group(1))))

        items = []
        for idx, (line_i, q_num) in enumerate(q_starts):
            block_end = q_starts[idx + 1][0] if idx + 1 < len(q_starts) else len(lines)
            block = lines[line_i:block_end]
            raw_text = "\n".join(block)
            joined = raw_text

            ans_match = re.search(r"CORRECT ANSWER:\s*([A-E])", joined)
            rat_split = re.split(r"\nRATIONALE\s*\n", joined, maxsplit=1)
            stem_part = rat_split[0] if rat_split else joined
            rest = rat_split[1] if len(rat_split) > 1 else ""

            ref_split = re.split(r"\nREFERENCES?\s*\n", rest, maxsplit=1)
            rationale_raw = ref_split[0] if ref_split else rest
            references_raw = ref_split[1] if len(ref_split) > 1 else ""

            stem_raw = re.sub(r"\nCORRECT ANSWER:.*", "", stem_part)
            stem_lines = stem_raw.split("\n")
            if stem_lines and stem_lines[0].strip().startswith("Question"):
                stem_lines = stem_lines[1:]

            stem_chunk, options, current = [], {}, None
            for raw_line in stem_lines:
                s = raw_line.strip()
                if not s:
                    continue
                m = OPTION_LINE_RE.match(s)
                if m:
                    current = m.group(1)
                    options[current] = [m.group(2)]
                elif current:
                    options[current].append(s)
                else:
                    stem_chunk.append(s)

            question_text = clean_prose(stem_chunk)
            option_texts = {k: clean_prose(v) for k, v in options.items()}
            explanation_text = clean_prose(rationale_raw.split("\n"))
            references_text = clean_prose(references_raw.split("\n"))
            correct_letter = ans_match.group(1) if ans_match else None

            items.append(self._build_item(
                q_num, question_text, option_texts, correct_letter,
                explanation_text, references_text, raw_text,
                source_location={"line_offset": line_i},
            ))
        return items

    # ---------- Type B: "QUESTIONS" section (numbered) + separate "ANSWERS" section (numbered + lettered) ----------

    def _extract_type_b(self, chapter_text: str) -> list:
        q_section_split = re.split(r"^\s*QUESTIONS\s*$", chapter_text, maxsplit=1, flags=re.MULTILINE | re.IGNORECASE)
        after_q = q_section_split[1] if len(q_section_split) > 1 else chapter_text

        a_section_split = re.split(r"^\s*ANSWERS\s*$", after_q, maxsplit=1, flags=re.MULTILINE | re.IGNORECASE)
        questions_block = a_section_split[0]
        answers_block = a_section_split[1] if len(a_section_split) > 1 else ""

        questions = self._parse_type_b_questions(questions_block)
        answers = self._parse_type_b_answers(answers_block)

        items = []
        for q_num, (question_text, option_texts, raw_q_text) in questions.items():
            correct_letter, explanation_text, raw_a_text = answers.get(q_num, (None, "", ""))
            items.append(self._build_item(
                q_num, question_text, option_texts, correct_letter,
                explanation_text, references_text="",
                raw_text=(raw_q_text + "\n---ANSWER---\n" + raw_a_text),
                source_location={},
            ))
        return items

    def _parse_type_b_questions(self, block: str):
        lines = block.split("\n")
        starts = []
        for i, line in enumerate(lines):
            m = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
            if m:
                starts.append((i, int(m.group(1)), m.group(2)))

        out = {}
        for idx, (line_i, q_num, first_content) in enumerate(starts):
            end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
            block_lines = [first_content] + lines[line_i + 1:end]
            raw_text = "\n".join(block_lines)

            stem_chunk, options, current = [], {}, None
            for raw_line in block_lines:
                s = raw_line.strip()
                if not s:
                    continue
                m = OPTION_LINE_RE.match(s)
                if m:
                    current = m.group(1)
                    options[current] = [m.group(2)]
                elif current:
                    options[current].append(s)
                else:
                    stem_chunk.append(s)

            question_text = clean_prose(stem_chunk)
            option_texts = {k: clean_prose(v) for k, v in options.items()}
            out[q_num] = (question_text, option_texts, raw_text)
        return out

    def _parse_type_b_answers(self, block: str):
        lines = block.split("\n")
        starts = []
        for i, line in enumerate(lines):
            m = re.match(r"^(\d+)\.\s*([A-E])\.?\s+(.*)$", line.strip())
            if m:
                starts.append((i, int(m.group(1)), m.group(2), m.group(3)))

        out = {}
        for idx, (line_i, q_num, letter, first_content) in enumerate(starts):
            end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
            block_lines = [first_content] + lines[line_i + 1:end]
            raw_text = "\n".join(block_lines)
            explanation_text = clean_prose(block_lines)
            out[q_num] = (letter, explanation_text, raw_text)
        return out

    # ---------- shared item assembly + confidence scoring ----------

    def _build_item(self, q_num, question_text, option_texts, correct_letter,
                     explanation_text, references_text, raw_text, source_location):
        confidence = "high"
        flags = []
        if correct_letter is None:
            confidence = "low"
            flags.append("no_correct_answer_found")
        if len(option_texts) < 4:
            confidence = "low"
            flags.append(f"only_{len(option_texts)}_options_found")
        if correct_letter and correct_letter not in option_texts:
            confidence = "low"
            flags.append("correct_letter_not_among_options")
        if not explanation_text:
            confidence = "medium" if confidence == "high" else confidence
            flags.append("empty_explanation")

        mismatch_flag, mismatch_evidence = check_rationale_answer_consistency(
            explanation_text, option_texts, correct_letter
        )
        if mismatch_flag:
            confidence = "medium" if confidence == "high" else confidence
            flags.append(mismatch_flag)

        payload = build_payload(
            question_text=question_text,
            options=[{"letter": l, "text": option_texts[l]} for l in sorted(option_texts.keys())],
            correct_answer=correct_letter,
            explanation_text=explanation_text,
            references=references_text,
        )

        return ExtractedItem(
            item_number=q_num,
            payload=payload,
            source_location=source_location,
            raw_extracted_text=raw_text,
            confidence_flag=confidence,
            review_flags=flags,
            review_evidence=mismatch_evidence if mismatch_flag else None,
        )
