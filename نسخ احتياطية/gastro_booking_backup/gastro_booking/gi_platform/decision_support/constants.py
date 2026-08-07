"""Clinical Decision Support — shared constants."""

from __future__ import annotations

RULE_KIND_PRIOR = 'differential_prior'
RULE_KIND_WEIGHT = 'weight_rule'
RULE_KIND_QUESTION = 'question_rule'
RULE_KIND_INVESTIGATION_BASELINE = 'investigation_baseline'
RULE_KIND_INVESTIGATION_ADVANCED = 'investigation_advanced'
RULE_KIND_RED_FLAG = 'red_flag'
RULE_KIND_SCORE_VARIABLE = 'score_variable'
RULE_KIND_BRANCH_ACTIVATION = 'branch_activation'

# Gastro25 catalogue_migrate uses short rule_kind aliases — normalized in knowledge_accessor.
RULE_KIND_ALIASES: dict[str, str] = {
    'prior': RULE_KIND_PRIOR,
    'weight': RULE_KIND_WEIGHT,
    'question': RULE_KIND_QUESTION,
    'red_flag': RULE_KIND_RED_FLAG,
    'investigation_baseline': RULE_KIND_INVESTIGATION_BASELINE,
    'investigation_advanced': RULE_KIND_INVESTIGATION_ADVANCED,
    'branch_activation': RULE_KIND_BRANCH_ACTIVATION,
}

CONSIDERATION_STRONG = 'strong_consideration'
CONSIDERATION_MODERATE = 'consider'
CONSIDERATION_LOW = 'less_likely'

DISPLAY_CONSIDERATION = {
    CONSIDERATION_STRONG: 'Strong consideration',
    CONSIDERATION_MODERATE: 'Consider',
    CONSIDERATION_LOW: 'Less likely',
}

TIER_BASELINE = 'baseline'
TIER_ADVANCED = 'advanced'

SOURCE_ANSWER = 'history_answer'
SOURCE_LAB = 'lab_result'
SOURCE_DEMOGRAPHIC = 'demographic'
SOURCE_DIAGNOSIS = 'diagnosis'

PURPOSE_ALARM = 'alarm'
PURPOSE_EXCLUDES = 'excludes'
PURPOSE_SUPPORTS = 'supports'
PURPOSE_CONTEXTUAL = 'contextual'
PURPOSE_RISK = 'risk_factor'

FORMULA_POINT_SUM = 'point_sum'
FORMULA_INTEGER_SUM = 'integer_sum'

OBJECT_TYPE_CDS_RULE = 'cds_rule'
OBJECT_TYPE_DISEASE = 'disease'
OBJECT_TYPE_GUIDELINE = 'guideline'
OBJECT_TYPE_HISTORY_QUESTION = 'history_question'
OBJECT_TYPE_INVESTIGATION = 'investigation'
OBJECT_TYPE_MANAGEMENT = 'management'
OBJECT_TYPE_SCORE = 'score'
STATUS_PUBLISHED = 'published'

PROVIDER_KEY = 'sqlite_knowledge'
