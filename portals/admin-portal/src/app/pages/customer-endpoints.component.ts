import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, AuditEntry, Customer } from '../core/api.service';

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
        <span class="actions">
          <button class="ghost" (click)="view(c)">View endpoints</button>
          <button class="ghost" (click)="viewActivity(c)">View activity</button>
          <button class="ghost" (click)="unlock(c)" [disabled]="busy() === c.id">Unlock</button>
        </span>
      </div>
      <p class="ok small" *ngIf="msg()[c.id]">{{ msg()[c.id] }}</p>
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
      <table *ngIf="activity()[c.id]">
        <thead><tr><th>When</th><th>Event</th><th>Detail</th></tr></thead>
        <tbody>
          <tr *ngFor="let a of activity()[c.id]">
            <td class="mono">{{ a.created_at | date: 'short' }}</td>
            <td class="mono">{{ a.action }}</td>
            <td class="muted">{{ a.target || '' }}</td>
          </tr>
          <tr *ngIf="activity()[c.id].length === 0">
            <td colspan="3" class="muted">No activity.</td>
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
      .actions { display: flex; gap: 8px; }
      table { margin-top: 10px; }
      .mono { font-family: monospace; font-size: 12px; }
    `,
  ],
})
export class CustomerEndpointsComponent {
  private api = inject(ApiService);
  term = '';
  searched = signal(false);
  customers = signal<Customer[]>([]);
  connections = signal<Record<string, any[]>>({});
  activity = signal<Record<string, AuditEntry[]>>({});
  busy = signal<string | null>(null);
  msg = signal<Record<string, string>>({});

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

  viewActivity(c: Customer): void {
    this.api.customerActivity(c.id).subscribe({
      next: (acts) => this.activity.update((m) => ({ ...m, [c.id]: acts })),
      error: () => this.activity.update((m) => ({ ...m, [c.id]: [] })),
    });
  }

  unlock(c: Customer): void {
    this.busy.set(c.id);
    this.api.unlockCustomer(c.id).subscribe({
      next: (r) => {
        this.busy.set(null);
        this.msg.update((m) => ({ ...m, [c.id]: r.message }));
      },
      error: () => {
        this.busy.set(null);
        this.msg.update((m) => ({ ...m, [c.id]: 'Unlock failed.' }));
      },
    });
  }
}
