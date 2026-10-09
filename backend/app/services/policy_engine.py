"""
Deterministic decision engine. Pure, unit-testable. ZERO LLM calls, ZERO
network calls, ever — this is what makes the demo auditable. This is the
ONLY thing in the project that decides approve/exception/fraud; Ollama
(Phase 2) never makes this call, it only extracts fields and explains
decisions after the fact.
"""
from decimal import Decimal, InvalidOperation

AMOUNT_TOLERANCE_PCT = Decimal("0.02")
QUANTITY_TOLERANCE_PCT = Decimal("0.02")
AUTO_APPROVE_MAX_AMOUNT = Decimal("5000")


def evaluate(invoice: dict, po: dict | None, receipt: dict | None, is_duplicate: bool) -> dict:
    """
    Returns {"decision": ..., "rule_applied": ..., "amount_variance_pct": ...,
             "quantity_variance_pct": ...}
    """
    if is_duplicate:
        return _result("fraud_flag", "DUPLICATE_INVOICE_NUMBER")

    if po is None:
        return _result("exception", "NO_MATCHING_PO")

    if po.get("status") == "closed":
        return _result("exception", "PO_CLOSED")

    try:
        amount_variance = abs(invoice["amount"] - po["amount"]) / po["amount"]
    except (InvalidOperation, ZeroDivisionError, TypeError):
        return _result("exception", "PO_AMOUNT_INVALID")

    quantity_variance = None
    if receipt is not None and receipt.get("quantity_received") not in (None, 0):
        try:
            quantity_variance = abs(
                invoice.get("quantity", 0) - receipt["quantity_received"]
            ) / receipt["quantity_received"]
        except (InvalidOperation, ZeroDivisionError, TypeError):
            quantity_variance = None

    if quantity_variance is not None and quantity_variance > QUANTITY_TOLERANCE_PCT:
        return _result("exception", "QUANTITY_VARIANCE_EXCEEDS_GUARDRAIL",
                        amount_variance, quantity_variance)

    if amount_variance <= AMOUNT_TOLERANCE_PCT and invoice["amount"] <= AUTO_APPROVE_MAX_AMOUNT:
        return _result("auto_approved", "WITHIN_TOLERANCE_AND_THRESHOLD",
                        amount_variance, quantity_variance)

    return _result("exception", "AMOUNT_VARIANCE_OR_THRESHOLD_EXCEEDED",
                    amount_variance, quantity_variance)


def _result(decision, rule, amount_variance=None, quantity_variance=None):
    return {
        "decision": decision,
        "rule_applied": rule,
        "amount_variance_pct": amount_variance,
        "quantity_variance_pct": quantity_variance,
    }
