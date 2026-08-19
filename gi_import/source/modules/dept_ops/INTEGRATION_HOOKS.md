# Department Operations — Integration Hooks (Sprint 7C)

Owner modules call these hooks at workflow transition points.
All hooks live in `app/modules/dept_ops/events.py` and `workforce_integration.py`.

## Wired integrations (Sprint 7C completion)

| Owner module | Trigger | Hook |
|--------------|---------|------|
| `procedures/services.py` | `_transition_status` | `on_procedure_status_changed` |
| `procedures/services.py` | `assign_room` | `on_room_assigned` |
| `procedure_execution/services.py` | `set_outcome` (completed) | `on_procedure_completed` |
| `procedure_execution/services.py` | `update_team` | `on_procedure_team_updated` |

## Automated effects

| Event | Automatic action |
|-------|------------------|
| Procedure → in room | Room status → Occupied |
| Procedure → finished | Room status → Available |
| Procedure completed | Scope → Awaiting reprocessing; consumables auto-deducted |
| Reprocessing completed | Scope → Available |
| Team updated | Portfolio sync; room staff assignments updated |
| Staff on leave | Excluded from room assignment and available staff lists |

**Rule:** References clinical records by ID only — never duplicates patient or procedure data.
