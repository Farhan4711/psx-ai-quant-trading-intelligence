# Runbooks

Operational runbooks for on-call and maintenance. Each runbook covers a specific failure scenario or routine operation.

| Runbook | When to use |
|---|---|
| [prediction-service-down.md](./prediction-service-down.md) | psx-inference is not responding |
| [retrain-model-from-scratch.md](./retrain-model-from-scratch.md) | Full model retrain after data issues or baseline drift |
| [symbol-delisted.md](./symbol-delisted.md) | A PSX symbol gets delisted mid-session |
| [database-restore.md](./database-restore.md) | Full or partial Postgres restore from backup |
| [read-only-mode.md](./read-only-mode.md) | How to enable read-only mode during partial failures |

> These runbooks are stubs. They will be filled in as each feature is built.
> A runbook that doesn't exist when you need it at 2 AM is worse than useless.
