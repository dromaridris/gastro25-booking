"""Deterministic section content builder from clinical context."""

from __future__ import annotations

from typing import Any


class SectionBuilder:
    """Builds section drafts from structured context — does not invent clinical data."""

    SECTION_BUILDERS = {
        'chief_complaint': '_chief_complaint',
        'history_presenting': '_history_presenting',
        'past_history': '_past_history',
        'examination': '_examination',
        'investigations': '_investigations',
        'assessment': '_assessment',
        'plan': '_plan',
        'interval_events': '_interval_events',
        'current_status': '_current_status',
        'new_findings': '_new_findings',
        'admission_reason': '_admission_reason',
        'hospital_course': '_hospital_course',
        'procedures': '_procedures_section',
        'final_diagnosis': '_final_diagnosis',
        'treatment': '_treatment',
        'follow_up': '_follow_up',
        'referral_reason': '_referral_reason',
        'clinical_summary': '_clinical_summary',
        'request': '_request',
        'since_last_visit': '_since_last_visit',
    }

    def build_section(self, section_key: str, context: dict[str, Any]) -> dict[str, Any]:
        method_name = self.SECTION_BUILDERS.get(section_key, '_generic')
        builder = getattr(self, method_name)
        return builder(context, section_key)

    def _chief_complaint(self, ctx: dict, key: str) -> dict:
        complaint = (ctx.get('intake') or {}).get('chief_complaint')
        missing = [] if complaint else ['Chief complaint not documented in intake']
        content = complaint or '[Chief complaint not available — physician to complete]'
        return self._result(key, content, missing, [('clinical_intake', 'chief_complaint')])

    def _history_presenting(self, ctx: dict, key: str) -> dict:
        text = ctx.get('approved_history_text') or ''
        findings = ctx.get('structured_findings') or []
        missing = [] if text or findings else ['Approved structured history not available']
        if text:
            content = text[:2000]
        elif findings:
            lines = [
                f"- {f.get('label', f.get('question_id', 'finding'))}: {f.get('value', '')}"
                for f in findings[:10]
            ]
            content = 'Structured history:\n' + '\n'.join(lines)
        else:
            content = '[History not available — physician to complete from source records]'
        return self._result(key, content, missing, [('clinical_history_ai', 'approved_draft')])

    def _past_history(self, ctx: dict, key: str) -> dict:
        return self._result(
            key,
            '[Past history not captured in available structured data — physician to complete]',
            ['Past medical history not in structured intake'], [],
        )

    def _examination(self, ctx: dict, key: str) -> dict:
        text = (ctx.get('examination_text') or '').strip()
        if text:
            return self._result(key, text, [], [('gi_history_session', 'examination_text')])
        return self._result(
            key,
            '[Examination findings not in structured data — physician to complete]',
            ['Physical examination not documented'], [],
        )

    def _investigations(self, ctx: dict, key: str) -> dict:
        labs = ctx.get('laboratory_results') or []
        imaging = ctx.get('imaging_results') or []
        missing = [] if labs or imaging else ['No investigation results available']
        parts = []
        for lab in labs[:8]:
            parts.append(
                f"{lab.get('test_code')}: {lab.get('value')} {lab.get('unit') or ''} ({lab.get('abnormal_flag')})"
            )
        for img in imaging[:3]:
            if img.get('impression'):
                parts.append(f"Imaging: {img['impression'][:200]}")
        content = '\n'.join(parts) if parts else '[Investigations pending or not documented]'
        return self._result(key, content, missing, [('investigations', 'results')])

    def _assessment(self, ctx: dict, key: str) -> dict:
        diagnoses = ctx.get('working_diagnoses') or []
        suggestions = (ctx.get('assessment') or {}).get('suggestions') or []
        missing = [] if diagnoses or suggestions else ['No differential assessment available']
        names = diagnoses or [s.get('diagnosis_name') for s in suggestions[:5] if s.get('diagnosis_name')]
        content = 'Working diagnoses: ' + ', '.join(names) if names else '[Assessment to be completed by physician]'
        conflicts = self._detect_conflicts(ctx)
        return self._result(key, content, missing, [('clinical_assessment', 'differential')], conflicts)

    def _plan(self, ctx: dict, key: str) -> dict:
        mgmt = (ctx.get('management_plan') or {}).get('suggestions') or []
        missing = [] if mgmt else ['No management plan suggestions available']
        lines = [f"- {s.get('description', '')[:200]}" for s in mgmt[:6]]
        content = '\n'.join(lines) if lines else '[Plan to be completed by physician]'
        return self._result(key, content, missing, [('management_plan_ai', 'suggestions')])

    def _interval_events(self, ctx: dict, key: str) -> dict:
        journey = ctx.get('patient_journey') or {}
        events = journey.get('timeline') or []
        follow_ups = journey.get('follow_up_plans') or []
        parts = [f"- {e.get('title', e.get('event_type'))}" for e in events[:5]]
        if follow_ups:
            parts.append(f"- Follow-up plan: {follow_ups[0].get('related_condition', 'active')}")
        missing = [] if parts else ['No interval events documented']
        content = 'Interval events:\n' + '\n'.join(parts) if parts else '[No interval events recorded]'
        return self._result(key, content, missing, [('patient_journey', 'timeline')])

    def _current_status(self, ctx: dict, key: str) -> dict:
        complaint = (ctx.get('intake') or {}).get('chief_complaint') or 'presenting complaint'
        outcomes = (ctx.get('patient_journey') or {}).get('outcomes') or []
        status = outcomes[0].get('outcome') if outcomes else None
        content = f'Patient seen for {complaint}.'
        if status:
            content += f' Latest recorded outcome: {status}.'
        return self._result(key, content, [], [('patient_journey', 'outcomes')])

    def _new_findings(self, ctx: dict, key: str) -> dict:
        findings = (ctx.get('interpretation') or {}).get('findings') or []
        missing = [] if findings else ['No new interpretation findings']
        lines = [f"- {f.get('finding_title')}: {f.get('significance', '')[:120]}" for f in findings[:5]]
        content = '\n'.join(lines) if lines else '[No new findings documented]'
        return self._result(key, content, missing, [('clinical_interpretation', 'findings')])

    def _admission_reason(self, ctx: dict, key: str) -> dict:
        return self._chief_complaint(ctx, key)

    def _hospital_course(self, ctx: dict, key: str) -> dict:
        return self._interval_events(ctx, key)

    def _procedures_section(self, ctx: dict, key: str) -> dict:
        procs = ctx.get('procedures') or []
        missing = [] if procs else ['No procedures documented']
        content = '\n'.join(
            f"- Procedure session {p.get('session_id')}: {p.get('outcome') or 'pending'}" for p in procs
        ) or '[No procedures recorded]'
        return self._result(key, content, missing, [('procedure_execution', 'sessions')])

    def _final_diagnosis(self, ctx: dict, key: str) -> dict:
        return self._assessment(ctx, key)

    def _treatment(self, ctx: dict, key: str) -> dict:
        return self._plan(ctx, key)

    def _follow_up(self, ctx: dict, key: str) -> dict:
        plans = (ctx.get('patient_journey') or {}).get('follow_up_plans') or []
        mgmt_follow = [
            s for s in (ctx.get('management_plan') or {}).get('suggestions') or []
            if s.get('category') == 'follow_up'
        ]
        missing = [] if plans or mgmt_follow else ['Follow-up plan not documented']
        parts = []
        for p in plans[:2]:
            parts.append(
                f"- {p.get('related_condition')}: {p.get('recommended_interval_text') or p.get('reason', '')[:100]}"
            )
        for s in mgmt_follow[:2]:
            parts.append(f"- {s.get('description', '')[:120]}")
        content = '\n'.join(parts) if parts else '[Follow-up to be specified by physician]'
        refs = ctx.get('knowledge_references') or []
        return self._result(key, content, missing, [('patient_journey', 'follow_up')], knowledge_refs=refs[:1])

    def _referral_reason(self, ctx: dict, key: str) -> dict:
        diagnoses = ctx.get('working_diagnoses') or []
        content = (
            f'Referral for specialist assessment of {diagnoses[0]}.'
            if diagnoses else '[Referral reason — physician to specify]'
        )
        missing = [] if diagnoses else ['Working diagnosis not established']
        return self._result(key, content, missing, [('clinical_assessment', 'diagnosis')])

    def _clinical_summary(self, ctx: dict, key: str) -> dict:
        parts = [self._chief_complaint(ctx, key)['content'], self._assessment(ctx, key)['content']]
        return self._result(
            key, '\n\n'.join(parts), [],
            [('clinical_intake', 'intake'), ('clinical_assessment', 'assessment')],
        )

    def _request(self, ctx: dict, key: str) -> dict:
        content = '[Specific referral request — physician to complete]'
        return self._result(key, content, ['Referral request details not in structured data'], [])

    def _since_last_visit(self, ctx: dict, key: str) -> dict:
        journey_ctx = ctx.get('patient_journey') or {}
        summaries = list(journey_ctx.get('follow_up_plans') or [])
        content = 'Since last visit: review interval events and current status.'
        if journey_ctx.get('outcomes'):
            content += f" Prior outcome: {journey_ctx['outcomes'][0].get('outcome')}."
        return self._result(
            key, content,
            [] if summaries or journey_ctx.get('timeline') else ['Limited follow-up history'],
            [('patient_journey', 'context')],
        )

    def _generic(self, ctx: dict, key: str) -> dict:
        return self._result(
            key, f"[Section '{key}' — physician to complete]",
            [f"No structured data mapped for section '{key}'"], [],
        )

    @staticmethod
    def _detect_conflicts(ctx: dict) -> list[str]:
        conflicts: list[str] = []
        assessment_decisions = (ctx.get('assessment') or {}).get('decisions') or []
        interpretation = (ctx.get('interpretation') or {}).get('differential_updates') or []
        accepted = {
            d.get('diagnosis_name') for d in assessment_decisions if d.get('physician_status') == 'accepted'
        }
        less_likely = {
            u.get('diagnosis_name') for u in interpretation if u.get('update_direction') == 'less_likely'
        }
        for name in accepted & less_likely:
            conflicts.append(
                f"Interpretation suggests '{name}' less likely but physician accepted it in assessment"
            )
        return conflicts

    @staticmethod
    def _result(
        section_key: str, content: str, missing: list[str], sources: list[tuple[str, str]],
        conflicts: list[str] | None = None, knowledge_refs: list[dict] | None = None,
    ) -> dict:
        source_refs = [{'module': m, 'field': f} for m, f in sources]
        is_complete = bool(content) and not missing and '[physician to complete' not in content.lower()
        return {
            'section_key': section_key,
            'generated_content': content,
            'source_data_references': source_refs,
            'missing_information': missing,
            'conflicting_information': conflicts or [],
            'knowledge_references': knowledge_refs or [],
            'is_complete': is_complete,
        }
