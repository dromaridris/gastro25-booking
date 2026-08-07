# MCQ Bank — Daily Target

Optional per-user goal: how many MCQs to solve today.

- Settings live in `mcqbank_user_settings` (enabled, target count, solved count + date).
- Each graded practice answer (first time in a cycle) and each quiz submit increments today’s count.
- When `daily_solved_date` ≠ today, the UI shows `0 / target` (counter resets on read or next solve).
- Disable via Study → Daily target settings (uncheck Enable → Save); counter is hidden.
