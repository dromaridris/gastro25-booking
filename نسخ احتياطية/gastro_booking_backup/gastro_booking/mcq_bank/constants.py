"""Permission constants for the MCQ question bank module."""
from __future__ import annotations

# Confirmed with the user: exactly these four roles get management access
# (upload books, run extraction, review/approve/reject/edit questions,
# generate quizzes and assign them). Everyone else who can log in gets the
# student solving experience only.
CAN_MANAGE_MCQ_BANK = ('admin', 'hod', 'specialist', 'registrar')
