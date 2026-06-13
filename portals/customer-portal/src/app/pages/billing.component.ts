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
      <p class="muted">Balance due: {{ billing()?.balance_due ?? 0 }} {{ billing()?.currency ?? 'USD' }}</p>
      <p class="muted" *ngIf="(billing()?.receipts ?? []).length === 0">No receipts yet.</p>
      <div *ngFor="let r of billing()?.receipts ?? []">{{ r | json }}</div>
    </div>
  `,
})
export class BillingComponent {
  private api = inject(ApiService);
  billing = signal<any>(null);

  constructor() {
    this.api.billing().subscribe({ next: (b) => this.billing.set(b), error: () => {} });
  }
}
