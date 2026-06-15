import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../core/api.service';

@Component({
  selector: 'app-billing',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h2 class="page-title">Billing & Receipts</h2>

    <!-- Current KB subscription charges (plan price x stacks in use) -->
    <div class="card">
      <h3>Subscription charges</h3>
      <p class="muted" *ngIf="!sub()?.has_subscription">
        No active subscription. An admin can assign you a plan, then your Project KB
        charges appear here.
      </p>
      <ng-container *ngIf="sub()?.has_subscription">
        <p>Plan: <strong>{{ sub()?.plan_name }}</strong></p>
        <p class="muted" *ngIf="(sub()?.line_items || []).length === 0">
          No Project KBs provisioned yet — nothing to bill.
        </p>
        <table *ngIf="(sub()?.line_items || []).length">
          <thead><tr><th>Tech stack</th><th>KBs</th><th>Docs</th><th>Monthly cost</th></tr></thead>
          <tbody>
            <tr *ngFor="let li of sub()?.line_items">
              <td>{{ li.stack }}</td>
              <td>{{ li.kb_count }}</td>
              <td>{{ li.doc_count }}</td>
              <td>{{ li.monthly_cost }} {{ (sub()?.currency || 'usd') | uppercase }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td colspan="3"><strong>Monthly total</strong></td>
              <td><strong>{{ sub()?.monthly_total }} {{ (sub()?.currency || 'usd') | uppercase }}</strong></td>
            </tr>
          </tfoot>
        </table>
        <div class="actions" *ngIf="(sub()?.line_items || []).length">
          <button (click)="generateInvoice()" [disabled]="charging()">
            {{ charging() ? 'Generating…' : 'Generate invoice' }}
          </button>
          <span class="muted" *ngIf="invoiceMsg()">{{ invoiceMsg() }}</span>
        </div>
      </ng-container>
    </div>

    <!-- Stripe receipts -->
    <div class="card">
      <h3>Receipts</h3>
      <p class="muted" *ngIf="!billing()?.configured">
        Billing is not configured (no Stripe key). Receipts appear here once billing is set up.
      </p>
      <ng-container *ngIf="billing()?.configured">
        <p>Balance due: <strong>{{ billing()?.balance_due }} {{ (billing()?.currency || 'usd') | uppercase }}</strong></p>
        <p class="muted" *ngIf="(billing()?.receipts || []).length === 0">No receipts yet.</p>
        <table *ngIf="(billing()?.receipts || []).length">
          <thead><tr><th>Invoice</th><th>Amount</th><th>Status</th><th></th></tr></thead>
          <tbody>
            <tr *ngFor="let r of billing()?.receipts">
              <td class="mono">{{ r.id }}</td>
              <td>{{ r.amount }} {{ (billing()?.currency || 'usd') | uppercase }}</td>
              <td>{{ r.status }}</td>
              <td><a *ngIf="r.url" [href]="r.url" target="_blank">view</a></td>
            </tr>
          </tbody>
        </table>
      </ng-container>
    </div>
  `,
  styles: [
    `
      table { width: 100%; border-collapse: collapse; margin-top: 10px; }
      th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); }
      tfoot td { border-top: 2px solid var(--border); border-bottom: none; }
      .mono { font-family: monospace; font-size: 12px; }
      .actions { margin-top: 14px; display: flex; align-items: center; gap: 12px; }
    `,
  ],
})
export class BillingComponent {
  private api = inject(ApiService);
  billing = signal<any>(null);
  sub = signal<any>(null);
  charging = signal(false);
  invoiceMsg = signal('');

  constructor() {
    this.load();
  }

  private load() {
    this.api.billing().subscribe({
      next: (b) => {
        this.billing.set(b);
        this.sub.set(b?.subscription || null);
      },
      error: () => {},
    });
  }

  generateInvoice() {
    this.charging.set(true);
    this.invoiceMsg.set('');
    this.api.chargeSubscription().subscribe({
      next: (r) => {
        this.charging.set(false);
        if (r?.configured && r?.invoice_id) {
          this.invoiceMsg.set(`Invoice ${r.invoice_id} created (${r.amount} ${(r.currency || 'usd').toUpperCase()}).`);
          this.load();
        } else if (r?.status === 'stripe_not_configured') {
          this.invoiceMsg.set(`Stripe not configured — would bill ${r.amount} ${(r.currency || 'usd').toUpperCase()}.`);
        } else if (r?.status === 'nothing_to_bill') {
          this.invoiceMsg.set('Nothing to bill this period.');
        } else {
          this.invoiceMsg.set('Could not generate invoice.');
        }
      },
      error: () => {
        this.charging.set(false);
        this.invoiceMsg.set('Could not generate invoice.');
      },
    });
  }
}
