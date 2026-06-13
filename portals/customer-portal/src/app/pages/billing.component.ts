import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../core/api.service';

@Component({
  selector: 'app-billing',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h2 class="page-title">Billing & Receipts</h2>
    <div class="card">
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
      .mono { font-family: monospace; font-size: 12px; }
    `,
  ],
})
export class BillingComponent {
  private api = inject(ApiService);
  billing = signal<any>(null);

  constructor() {
    this.api.billing().subscribe({ next: (b) => this.billing.set(b), error: () => {} });
  }
}
