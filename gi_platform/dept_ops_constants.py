"""Unit Operations (dept_ops) constants — ported from GastroIntelligence."""

ROOM_AVAILABLE = 'available'
ROOM_OCCUPIED = 'occupied'
ROOM_CLEANING = 'cleaning'
ROOM_MAINTENANCE = 'maintenance'
ROOM_OUT_OF_SERVICE = 'out_of_service'
ALL_ROOM_STATUSES = (
    ROOM_AVAILABLE, ROOM_OCCUPIED, ROOM_CLEANING,
    ROOM_MAINTENANCE, ROOM_OUT_OF_SERVICE,
)

ALL_ROOM_TYPES = ('general', 'ercp', 'eus', 'recovery', 'other')

ALL_SCOPE_TYPES = (
    'gastroscope', 'colonoscope', 'duodenoscope', 'echoendoscope', 'pediatric', 'other',
)

SCOPE_AVAILABLE = 'available'
SCOPE_IN_PROCEDURE = 'in_procedure'
SCOPE_AWAITING_CLEANING = 'awaiting_cleaning'
SCOPE_CLEANING = 'cleaning'
SCOPE_READY = 'ready'
SCOPE_MAINTENANCE = 'maintenance'
SCOPE_OUT_OF_SERVICE = 'out_of_service'
ALL_SCOPE_STATUSES = (
    SCOPE_AVAILABLE, SCOPE_IN_PROCEDURE, SCOPE_AWAITING_CLEANING, SCOPE_CLEANING,
    SCOPE_READY, SCOPE_MAINTENANCE, SCOPE_OUT_OF_SERVICE,
)

REPROCESSING_STEPS = (
    'procedure_finished', 'sent_for_cleaning', 'leak_test', 'manual_cleaning',
    'high_level_disinfection', 'drying', 'storage', 'ready_again',
)

ALL_CONSUMABLE_CATEGORIES = (
    'stent', 'snare', 'injection_needle', 'guidewire', 'sphincterotome', 'balloon',
    'clip', 'hemostatic', 'biopsy_forceps', 'cytology_brush', 'peg_kit', 'dilator', 'other',
)

STOCK_USAGE = 'usage'
STOCK_RECEIPT = 'receipt'
STOCK_ADJUSTMENT = 'adjustment'

WL_ACTIVE = 'active'
WL_SCHEDULED = 'scheduled'
WL_COMPLETED = 'completed'
WL_CANCELLED = 'cancelled'

ALL_SHIFT_TYPES = ('day', 'evening', 'on_call', 'leave', 'backup')
ALL_PRIORITIES = ('routine', 'urgent', 'emergency')

ANN_CATEGORIES = ('notice', 'department', 'holiday', 'equipment', 'academic')
MSG_SCOPES = ('direct', 'team', 'department')
