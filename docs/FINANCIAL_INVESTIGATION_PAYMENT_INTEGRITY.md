# Financial Investigation, Payment Integrity & Governed Remediation

Release 43 converts Release 42 read-only anomalies into durable human-owned investigation cases. The source financial/accounting records remain governed by Releases 40–41 and are never rewritten by this layer.

## Control flow

`Release 42 anomaly -> durable case -> immutable evidence pack -> human investigator lease -> human root cause -> remediation proposal -> second finance approval when material -> governed Release 40/41 referral -> reconciliation -> human closure`.

Cases cluster duplicate/overpayment and provider-pattern signals by provider/anomaly dimensions. Evidence packs retain source watermarks, ledger/financial citations, the original anomaly hash and related case IDs. Human annotations and case audit events are append-only.

AI output is recommendation-only. A human investigator must explicitly document disagreement when choosing a root cause different from the stored recommendation. Material payment holds, void/reissue referrals, adjustments and recoupments require an independent `finance_approver` before referral execution. Referral execution invokes existing governed workflows; it does not approve a payment, post a journal, change adjudication, alter reserves or move funds.
