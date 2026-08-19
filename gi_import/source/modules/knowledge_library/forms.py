"""Knowledge Library authoring forms."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from app.modules.knowledge_library.constants import ALL_OBJECT_TYPES, ALL_LINK_TYPES


class KnowledgeObjectFilterForm(FlaskForm):
    object_type = SelectField("Type", choices=[("", "All types")], validators=[Optional()])
    include_archived = BooleanField("Show archived")
    submit = SubmitField("Filter")


class KnowledgeObjectForm(FlaskForm):
    object_type = SelectField(
        "Object type",
        choices=[(t, t) for t in ALL_OBJECT_TYPES],
        validators=[DataRequired()],
    )
    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    stable_id = StringField(
        "Stable ID",
        validators=[DataRequired(), Length(max=100)],
        render_kw={"placeholder": "kl.disease.celiac"},
    )
    specialty_code = StringField("Specialty code", validators=[Optional(), Length(max=50)])
    topic_key = StringField("Topic key", validators=[Optional(), Length(max=100)])
    version_label = StringField("Version label", default="1.0.0", validators=[Optional(), Length(max=40)])
    summary = TextAreaField("Summary", validators=[Optional()])
    body = TextAreaField("Full body (optional expansion text)", validators=[Optional()])
    attributes_json = TextAreaField(
        "Structured attributes (JSON)",
        validators=[Optional()],
        render_kw={
            "rows": 8,
            "placeholder": '{"rule_kind": "weight_rule", "complaint_code": "hist.diarrhea", ...}',
        },
    )
    submit = SubmitField("Save draft")


class ArchiveKnowledgeForm(FlaskForm):
    reason = StringField("Archive reason", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Archive")


class KnowledgeLinkForm(FlaskForm):
    to_stable_id = StringField("Target stable ID", validators=[DataRequired(), Length(max=100)])
    link_type = SelectField(
        "Link type",
        choices=[(t, t) for t in ALL_LINK_TYPES],
        validators=[DataRequired()],
    )
    submit = SubmitField("Add link")
