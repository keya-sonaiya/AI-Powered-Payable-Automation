// Synthetic OCR-style text blocks, in the same shape the n8n workflow's Code
// node generates from mock_dataset.json (see PROGRESS.md, Phase 2). These
// let the dashboard demo the full /ingest pipeline — OCR text in, decision
// out — without needing n8n running. Numbers are illustrative, not drawn
// from the actual seeded dataset, so re-running these will not exactly
// reproduce a specific historical decision.

export interface SampleInvoice {
  label: string;
  description: string;
  raw_text: string;
}

export const SAMPLE_INVOICES: SampleInvoice[] = [
  {
    label: "Clean match, low amount",
    description: "Should land on auto_approved — matches its PO exactly and is under the $5,000 ceiling.",
    raw_text:
      "INVOICE\nInvoice Number: INV-DEMO-2001\nVendor: Clark PLC\nPO Number: PO-100002\nAmount: $244.92\nQuantity: 13\nUnit Price: $18.84",
  },
  {
    label: "Amount variance",
    description: "Invoiced amount runs well above the matching PO — should land on exception.",
    raw_text:
      "INVOICE\nInvoice Number: INV-DEMO-1002\nVendor: Northwind Supply Co\nPO Number: PO-100042\nAmount: $3100.00\nQuantity: 50\nUnit Price: $62.00",
  },
  {
    label: "No matching PO",
    description: "References a PO number that doesn't exist — should land on exception under NO_MATCHING_PO.",
    raw_text:
      "INVOICE\nInvoice Number: INV-DEMO-1003\nVendor: Northwind Supply Co\nPO Number: PO-999999\nAmount: $1800.00\nQuantity: 20\nUnit Price: $90.00",
  },
];
