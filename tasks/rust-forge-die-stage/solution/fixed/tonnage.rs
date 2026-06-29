use crate::ledger::ForgeLedger;

pub fn recorded_tonnage(ledger: &ForgeLedger) -> u64 {
    ledger.total_tonnage()
}
