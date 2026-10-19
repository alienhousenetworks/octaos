"""Provider spend ledger. Paid work cannot start without a reservation."""
from app.services.sales_os.search_v4.contracts import UsageLedgerEntry, new_id


class BudgetLedger:
    def __init__(self, tenant_id: str, correlation_id: str, limit_inr: float):
        self.tenant_id = tenant_id
        self.correlation_id = correlation_id
        self.limit_inr = max(0.0, float(limit_inr))
        self.entries: list[UsageLedgerEntry] = []
        self._reserved = 0.0
        self._spent = 0.0

    def remaining(self) -> float:
        return round(self.limit_inr - self._spent - self._reserved, 6)

    def reserve(self, provider: str, operation: str, amount: float, task_id: str) -> UsageLedgerEntry:
        estimate = round(max(0.0, float(amount)), 6)
        entry = UsageLedgerEntry(
            entry_id=new_id(),
            tenant_id=self.tenant_id,
            correlation_id=self.correlation_id,
            provider=provider,
            operation=operation,
            estimated_cost_inr=estimate,
            actual_cost_inr=0.0,
            status="rejected",
            task_id=task_id,
        )
        if estimate > self.remaining() + 1e-9:
            self.entries.append(entry)
            return entry
        entry.status = "reserved"
        self._reserved += estimate
        self.entries.append(entry)
        return entry

    def reconcile(self, entry_id: str, actual_cost_inr: float) -> None:
        entry = self._entry(entry_id)
        if entry is None or entry.status != "reserved":
            return
        actual = round(max(0.0, float(actual_cost_inr)), 6)
        self._reserved = max(0.0, self._reserved - entry.estimated_cost_inr)
        self._spent += actual
        entry.actual_cost_inr = actual
        entry.status = "reconciled"

    def release(self, entry_id: str) -> None:
        entry = self._entry(entry_id)
        if entry is None or entry.status != "reserved":
            return
        self._reserved = max(0.0, self._reserved - entry.estimated_cost_inr)
        entry.actual_cost_inr = 0.0
        entry.status = "released"

    def spent(self) -> float:
        return round(self._spent, 6)

    def _entry(self, entry_id: str) -> UsageLedgerEntry | None:
        for entry in self.entries:
            if entry.entry_id == entry_id:
                return entry
        return None
