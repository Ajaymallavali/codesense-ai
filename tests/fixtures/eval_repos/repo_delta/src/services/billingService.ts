export interface InvoiceItem {
  id: string;
  name: string;
  unitPrice: number;
  quantity: number;
}

export function computeInvoiceSummary(items: InvoiceItem[], discountRate: number = 0.05): { subtotal: number; discount: number; finalTotal: number } {
  let subtotal = 0;
  for (const item of items) {
    subtotal += item.unitPrice * item.quantity;
  }
  const discount = subtotal * discountRate;
  const finalTotal = subtotal - discount;
  return { subtotal, discount, finalTotal };
}
