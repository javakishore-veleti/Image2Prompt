import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, Customer } from '../core/api.service';

@Component({
  selector: 'app-customer-endpoints',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h2 class="page-title">Customer Endpoints</h2>
    <p class="muted">Search a customer, then view the cloud file systems they've connected.</p>
    <div class="search-row">
      <input placeholder="Search by email or name…" [(ngModel)]="term" (keyup.enter)="search()" />
      <button (click)="search()">Search</button>
    </div>

    <div class="card" *ngFor="let c of customers()">
      <div class="cust">
        <div><strong>{{ c.email }}</strong> <span class="muted">{{ c.name || '' }}</span></div>
        <button class="ghost" (click)="view(c)">View endpoints</button>
      </div>
      <table *ngIf="connections()[c.id]">
        <thead><tr><th>Provider</th><th>Account</th><th>Status</th></tr></thead>
        <tbody>
          <tr *ngFor="let cn of connections()[c.id]">
            <td>{{ cn.display_name }}</td>
            <td>{{ cn.account_email }}</td>
            <td class="ok">{{ cn.status }}</td>
          </tr>
          <tr *ngIf="connections()[c.id].length === 0">
            <td colspan="3" class="muted">No connections.</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="muted" *ngIf="searched() && customers().length === 0">No matches.</p>
  `,
  styles: [
    `
      .search-row { display: flex; gap: 10px; margin-bottom: 18px; max-width: 520px; }
      .card { margin-bottom: 12px; }
      .cust { display: flex; justify-content: space-between; align-items: center; }
      table { margin-top: 10px; }
    `,
  ],
})
export class CustomerEndpointsComponent {
  private api = inject(ApiService);
  term = '';
  searched = signal(false);
  customers = signal<Customer[]>([]);
  connections = signal<Record<string, any[]>>({});

  search(): void {
    this.api.customers(this.term.trim() || undefined).subscribe({
      next: (c) => {
        this.customers.set(c);
        this.searched.set(true);
      },
      error: () => {},
    });
  }

  view(c: Customer): void {
    this.api.customerConnections(c.id).subscribe({
      next: (conns) => this.connections.update((m) => ({ ...m, [c.id]: conns })),
      error: () => this.connections.update((m) => ({ ...m, [c.id]: [] })),
    });
  }
}
