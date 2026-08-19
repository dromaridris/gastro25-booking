"""Clinical Decision Support — shared constants (specialty-agnostic)."""

RULE_KIND_PRIOR = "differential_prior"
RULE_KIND_WEIGHT = "weight_rule"
RULE_KIND_QUESTION = "question_rule"
RULE_KIND_INVESTIGATION_BASELINE = "investigation_baseline"
RULE_KIND_INVESTIGATION_ADVANCED = "investigation_advanced"
RULE_KIND_RED_FLAG = "red_flag"
RULE_KIND_SCORE_VARIABLE = "score_variable"
RULE_KIND_BRANCH_ACTIVATION = "branch_activation"

CONSIDERATION_STRONG = "strong_consideration"
CONSIDERATION_MODERATE = "consider"
CONSIDERATION_LOW = "less_likely"

DISPLAY_CONSIDERATION = {
    CONSIDERATION_STRONG: "Strong consideration",
    CONSIDERATION_MODERATE: "Consider",
    CONSIDERATION_LOW: "Less likely",
}

TIER_BASELINE = "baseline"
TIER_ADVANCED = "advanced"

SOURCE_ANSWER = "history_answer"
SOURCE_LAB = "lab_result"
SOURCE_DEMOGRAPHIC = "demographic"
SOURCE_DIAGNOSIS = "diagnosis"

PURPOSE_ALARM = "alarm"
PURPOSE_EXCLUDES = "excludes"
PURPOSE_SUPPORTS = "supports"
PURPOSE_CONTEXTUAL = "contextual"
PURPOSE_RISK = "risk_factor"

FORMULA_POINT_SUM = "point_sum"
FORMULA_INTEGER_SUM = "integer_sum"
