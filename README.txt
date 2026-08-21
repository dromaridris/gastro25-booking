Gastro25 safe scoped updater
Baseline: e7dc8ea713767632b52c3483e8ebb0109f808b2d

1. Extract this ZIP anywhere outside the gastro_booking project (Downloads is fine).
2. In Git Bash, enter the gastro_booking project folder and run `git sync`.
3. Type `python `, drag apply_safe_update.py from the extracted folder into Git Bash,
   then press Enter. This runs the updater without copying it into the project.
4. After SUCCESS, run:

   python -m pytest -q
   git diff --check
   git sync

The updater stops without changing anything unless all five source files exactly
match the approved GitHub baseline. It creates a timestamped code backup outside
the repository before writing. It does not modify the database, image folders,
or print templates.
