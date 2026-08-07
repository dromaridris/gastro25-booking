"""Endoscopy booking capacity settings — forms."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional


class BookingCapacitySettingsForm(FlaskForm):
    upper_gi_daily_cap = IntegerField(
        "Upper GI daily cap",
        validators=[DataRequired(), NumberRange(min=0, max=200)],
    )
    colonoscopy_daily_cap = IntegerField(
        "Colonoscopy daily cap",
        validators=[DataRequired(), NumberRange(min=0, max=200)],
    )
    peg_daily_cap = IntegerField(
        "PEG daily cap",
        validators=[DataRequired(), NumberRange(min=0, max=50)],
    )
    scheduler_sub_quota_percent = IntegerField(
        "Reception sub-quota (%)",
        validators=[DataRequired(), NumberRange(min=0, max=100)],
    )
    time_lock_hours = IntegerField(
        "Reception minimum advance booking (hours)",
        validators=[DataRequired(), NumberRange(min=0, max=720)],
    )
    sunday_blocked = BooleanField("Block Sunday bookings")
    ercp_weekdays_only = BooleanField("ERCP on Tuesday and Saturday only")
    submit = SubmitField("Save capacity settings")


class BookingHolidayForm(FlaskForm):
    holiday_date = DateField("Holiday date", validators=[DataRequired()])
    label = StringField("Label (optional)", validators=[Optional()])
    submit = SubmitField("Add holiday")
