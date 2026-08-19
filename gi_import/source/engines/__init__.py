"""
app/engines/ holds every reusable, cross-cutting engine per the project's
"never duplicate code — build one engine per concern" rule:
PermissionEngine and AuditEngine now; ProcedureEngine, ReportEngine,
ImageEngine, AIEngine, and SearchEngine arrive in later sprints as their
respective modules are built. Every module calls into these — no module
re-implements permission checking or audit logging on its own.
"""
