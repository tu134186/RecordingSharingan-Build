# RecordingSharingan 6.24

Crash fix: never sets masksToBounds (portal views), no setFrame in force-apply,
all island hooks wrapped in try/catch with re-entrancy guard.

See FIX-6.24.md.
