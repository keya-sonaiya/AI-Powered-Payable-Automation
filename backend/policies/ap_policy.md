# Accounts Payable Policy — AP Agent Demo

This document defines the guardrails enforced by `policy_engine.py`. Each
section below corresponds to one `rule_applied` value the engine can return,
so it can be embedded and retrieved clause-by-clause (Phase 2, via Chroma).

## Auto-Approval Threshold (WITHIN_TOLERANCE_AND_THRESHOLD)

Invoices may be auto-approved without human review only when both of the
following hold: the invoice amount is within 2% of the matching purchase
order's amount, AND the invoice total does not exceed $5,000. Invoices
above this threshold always require manual review regardless of how closely
they match their PO, since larger dollar amounts carry proportionally
higher risk if a match is coincidentally close but still wrong.

## Amount Variance Guardrail (AMOUNT_VARIANCE_OR_THRESHOLD_EXCEEDED)

Any invoice whose amount differs from its matching purchase order's amount
by more than 2% is routed to exception queue for manual review. This
protects against billing errors, unauthorized price changes, and vendor
overcharges that a purely automated system should not wave through.

## Quantity Variance Guardrail (QUANTITY_VARIANCE_EXCEEDS_GUARDRAIL)

A genuine three-way match compares invoiced quantity against received
quantity (from the goods receipt), not just dollar amounts. If the invoiced
quantity differs from the receipt's recorded quantity by more than 2%, the
invoice is routed to exception queue — even if the dollar amount happens to
match the purchase order. This catches cases such as being billed for more
units than were actually delivered.

## No Matching Purchase Order (NO_MATCHING_PO)

If an invoice references a PO number that does not exist in the system, it
cannot be matched and is automatically routed to exception queue. This is
treated as a routing decision, not a system error — a missing PO is a
common and expected real-world scenario (e.g. a vendor citing the wrong PO
number), not a pipeline failure.

## Closed Purchase Order (PO_CLOSED)

Invoices against a purchase order whose status is "closed" are
automatically routed to exception queue, regardless of amount or quantity
match. A closed PO indicates the order was already fully invoiced and
settled; any further invoice against it is treated as suspicious or
erroneous until a human confirms otherwise.

## Duplicate Invoice Detection (DUPLICATE_INVOICE_NUMBER)

An invoice is flagged as a potential fraud/duplicate submission if its
invoice number has already been recorded for the same vendor. The
duplicate check is keyed on the pair (vendor ID, invoice number) — not on
invoice number alone — since different vendors may legitimately reuse the
same invoice numbering scheme. A detected duplicate is routed straight to
the fraud_flag decision, bypassing all other checks, since a resubmitted
invoice number is a stronger risk signal than an amount or quantity
mismatch.

## Invalid Purchase Order Amount (PO_AMOUNT_INVALID)

If the matching purchase order's amount is missing, zero, or otherwise
cannot be used to compute a variance percentage, the invoice is routed to
exception queue rather than allowed to crash the pipeline or silently pass
through as approved.
