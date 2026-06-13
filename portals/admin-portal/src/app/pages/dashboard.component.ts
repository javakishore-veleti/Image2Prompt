import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../core/api.service';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h2 class="page-title">Dashboard</h2>
    <div class="stats">
      <div class="card stat">
        <div class="num">{{ customerCount() }}</div>
        <div class="muted">Customers</div>
      </div>
      <div class="card stat">
        <div class="num">{{ providerCount() }}</div>
        <div class="muted">Providers</div>
      </div>
      <div class="card stat">
        <div class="num">{{ enabledCount() }}</div>
        <div class="muted">Enabled providers</div>
      </div>
    </div>
    <p class="muted">Analytics widgets are stubbed for this build.</p>
  `,
  styles: [
    `
      .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 18px; }
      .stat { text-align: center; }
      .num { font-size: 32px; font-weight: 800; color: var(--brand); }
    `,
  ],
})
export class DashboardComponent {
  private api = inject(ApiService);
  customerCount = signal(0);
  providerCount = signal(0);
  enabledCount = signal(0);

  constructor() {
    forkJoin({ customers: this.api.customers(), providers: this.api.providers() }).subscribe({
      next: ({ customers, providers }) => {
        this.customerCount.set(customers.length);
        this.providerCount.set(providers.length);
        this.enabledCount.set(providers.filter((p) => p.enabled).length);
      },
      error: () => {},
    });
  }
}
