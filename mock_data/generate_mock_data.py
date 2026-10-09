"""
Generates mock_dataset.json for the AP Agent Demo.

Fixes vs. the original draft:
  (a) no dead branches — every scenario produces a genuinely different outcome
  (b) "no matching PO" scenario: invoice references a po_number that doesn't exist
  (c) "quantity mismatch" scenario, now that quantity fields exist
  (d) "closed PO" scenario
  (e) duplicates are tagged BEFORE building the final list, not sampled after
      the fact from the finished list

Target mix: ~55% clean match, 10% amount mismatch, 10% quantity mismatch,
10% no matching PO, 5% closed PO, 10% duplicate.

Output: mock_data/output/mock_dataset.json
"""
import json
import os
import random
from decimal import Decimal

from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

TOTAL_INVOICES = 200

SCENARIO_WEIGHTS = {
    "clean_match": 0.55,
    "amount_mismatch": 0.10,
    "quantity_mismatch": 0.10,
    "no_matching_po": 0.10,
    "closed_po": 0.05,
    "duplicate": 0.10,
}


def build_scenario_plan(total: int) -> list[str]:
    """
    Decide the scenario for every invoice UP FRONT, as an explicit list, so
    intent (especially which invoices are duplicates) is baked in before any
    invoice objects are built — never sampled after the fact from a finished
    list.
    """
    plan = []
    for scenario, weight in SCENARIO_WEIGHTS.items():
        count = round(total * weight)
        plan.extend([scenario] * count)

    # Rounding can leave us a few short/over TOTAL_INVOICES; pad/trim using
    # the largest bucket (clean_match) so the target ratios stay accurate.
    while len(plan) < total:
        plan.append("clean_match")
    while len(plan) > total:
        plan.remove("clean_match")

    random.shuffle(plan)
    return plan


def make_vendor(vendor_id: int) -> dict:
    return {
        "id": vendor_id,
        "name": fake.company(),
        "tax_id": fake.numerify("##-#######"),
        "payment_terms": random.choice(["Net 30", "Net 45", "Net 60"]),
    }


def make_po(po_id: int, vendor_id: int, status: str = "open") -> dict:
    quantity = random.randint(10, 500)
    unit_price = round(random.uniform(5, 200), 2)
    return {
        "id": po_id,
        "po_number": f"PO-{100000 + po_id}",
        "vendor_id": vendor_id,
        "amount": round(quantity * unit_price, 2),
        "quantity": quantity,
        "unit_price": unit_price,
        "status": status,
    }


def make_receipt(receipt_id: int, po_id: int, quantity_received: int) -> dict:
    return {
        "id": receipt_id,
        "po_id": po_id,
        "quantity_received": quantity_received,
        "received_date": fake.date_this_year().isoformat(),
    }


def make_invoice_shell(invoice_id: int, vendor_id: int, po_number: str | None,
                        amount, quantity, unit_price) -> dict:
    return {
        "id": invoice_id,
        "invoice_number": f"INV-{fake.unique.random_number(digits=8)}",
        "vendor_id": vendor_id,
        "po_number": po_number,
        "amount": float(amount),
        "quantity": quantity,
        "unit_price": float(unit_price),
        "raw_ocr_text": None,   # Phase 2 populates via OCR
        "extracted_json": None,  # Phase 2 populates via LLM extraction
    }


def generate(total: int = TOTAL_INVOICES) -> dict:
    scenario_plan = build_scenario_plan(total)

    vendors = [make_vendor(i) for i in range(1, 21)]
    purchase_orders = []
    receipts = []
    invoices = []

    next_po_id = 1
    next_receipt_id = 1
    next_invoice_id = 1

    # Track which (vendor_id, invoice_number) pairs already exist so a
    # "duplicate" scenario can genuinely reuse one, rather than coincidentally
    # generating a fresh number that happens to collide.
    issued_invoice_numbers_by_vendor: dict[int, list[str]] = {}

    for scenario in scenario_plan:
        vendor = random.choice(vendors)
        vendor_id = vendor["id"]

        if scenario == "clean_match":
            po = make_po(next_po_id, vendor_id, status="open")
            next_po_id += 1
            purchase_orders.append(po)

            receipt = make_receipt(next_receipt_id, po["id"], po["quantity"])
            next_receipt_id += 1
            receipts.append(receipt)

            invoice = make_invoice_shell(
                next_invoice_id, vendor_id, po["po_number"],
                po["amount"], po["quantity"], po["unit_price"],
            )

        elif scenario == "amount_mismatch":
            po = make_po(next_po_id, vendor_id, status="open")
            next_po_id += 1
            purchase_orders.append(po)

            receipt = make_receipt(next_receipt_id, po["id"], po["quantity"])
            next_receipt_id += 1
            receipts.append(receipt)

            # Push amount well outside the 2% tolerance.
            skewed_amount = Decimal(str(po["amount"])) * Decimal("1.15")
            invoice = make_invoice_shell(
                next_invoice_id, vendor_id, po["po_number"],
                skewed_amount, po["quantity"], po["unit_price"],
            )

        elif scenario == "quantity_mismatch":
            po = make_po(next_po_id, vendor_id, status="open")
            next_po_id += 1
            purchase_orders.append(po)

            # Receipt shows fewer units received than the PO/invoice claim.
            received_qty = max(1, int(po["quantity"] * 0.80))
            receipt = make_receipt(next_receipt_id, po["id"], received_qty)
            next_receipt_id += 1
            receipts.append(receipt)

            invoice = make_invoice_shell(
                next_invoice_id, vendor_id, po["po_number"],
                po["amount"], po["quantity"], po["unit_price"],
            )

        elif scenario == "no_matching_po":
            # Reference a PO number that will never be created.
            fake_po_number = f"PO-{900000 + next_invoice_id}"
            amount = round(random.uniform(100, 3000), 2)
            quantity = random.randint(5, 50)
            unit_price = round(amount / quantity, 2)
            invoice = make_invoice_shell(
                next_invoice_id, vendor_id, fake_po_number,
                amount, quantity, unit_price,
            )

        elif scenario == "closed_po":
            po = make_po(next_po_id, vendor_id, status="closed")
            next_po_id += 1
            purchase_orders.append(po)

            receipt = make_receipt(next_receipt_id, po["id"], po["quantity"])
            next_receipt_id += 1
            receipts.append(receipt)

            invoice = make_invoice_shell(
                next_invoice_id, vendor_id, po["po_number"],
                po["amount"], po["quantity"], po["unit_price"],
            )

        elif scenario == "duplicate":
            existing = issued_invoice_numbers_by_vendor.get(vendor_id)
            if existing:
                # Reuse a real prior invoice number for this same vendor.
                po = make_po(next_po_id, vendor_id, status="open")
                next_po_id += 1
                purchase_orders.append(po)

                receipt = make_receipt(next_receipt_id, po["id"], po["quantity"])
                next_receipt_id += 1
                receipts.append(receipt)

                invoice = make_invoice_shell(
                    next_invoice_id, vendor_id, po["po_number"],
                    po["amount"], po["quantity"], po["unit_price"],
                )
                invoice["invoice_number"] = random.choice(existing)
            else:
                # No prior invoice for this vendor yet — fall back to a clean
                # match instead of faking a duplicate that isn't one. This
                # keeps the mix honest rather than adding a dead branch.
                po = make_po(next_po_id, vendor_id, status="open")
                next_po_id += 1
                purchase_orders.append(po)

                receipt = make_receipt(next_receipt_id, po["id"], po["quantity"])
                next_receipt_id += 1
                receipts.append(receipt)

                invoice = make_invoice_shell(
                    next_invoice_id, vendor_id, po["po_number"],
                    po["amount"], po["quantity"], po["unit_price"],
                )

        else:
            raise ValueError(f"Unknown scenario: {scenario}")

        invoice["_scenario"] = scenario  # for reporting/debugging only
        invoices.append(invoice)
        issued_invoice_numbers_by_vendor.setdefault(vendor_id, []).append(
            invoice["invoice_number"]
        )
        next_invoice_id += 1

    return {
        "vendors": vendors,
        "purchase_orders": purchase_orders,
        "receipts": receipts,
        "invoices": invoices,
    }


def main():
    dataset = generate()

    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "mock_dataset.json")

    with open(out_path, "w") as f:
        json.dump(dataset, f, indent=2)

    counts: dict[str, int] = {}
    for inv in dataset["invoices"]:
        counts[inv["_scenario"]] = counts.get(inv["_scenario"], 0) + 1

    print(f"Wrote {len(dataset['invoices'])} invoices to {out_path}")
    print(f"Vendors: {len(dataset['vendors'])}")
    print(f"Purchase orders: {len(dataset['purchase_orders'])}")
    print(f"Receipts: {len(dataset['receipts'])}")
    print("Scenario counts:")
    for scenario, count in sorted(counts.items()):
        pct = 100 * count / len(dataset["invoices"])
        print(f"  {scenario:20s} {count:4d}  ({pct:.1f}%)")


if __name__ == "__main__":
    main()
