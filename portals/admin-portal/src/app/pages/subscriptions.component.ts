import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, Plan, SubscriptionRow } from '../core/api.service';

@Component({
  selector: 'app-subscriptions',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h2 class="page-title">Subscriptions</h2>
    <p class="muted">Define plans that price and allow KB vector-store tech stacks, then assign customers.</p>

    <div class="card create">
      <h3>Create plan</h3>
      <div class="field"><label>Name</label><input [(ngModel)]="name" placeholder="e.g. Pro" /></div>
      <div class="field"><label>Description</label><input [(ngModel)]="description" /></div>
      <div class="field">
        <label>Tech stacks &amp; monthly cost</label>
        <div class="stacks">
          <label class="stack" *ngFor="let s of stacks()">
            <input type="checkbox" [checked]="picked(s)" (change)="toggle(s)" /> {{ s }}
            <input class="cost" type="number" min="0" step="1" [(ngModel)]="cost[s]" [disabled]="!picked(s)" placeholder="$/mo" />
          </label>
        </div>
      </div>
      <p class="error" *ngIf="error()">{{ error() }}</p>
      <button (click)="create()" [disabled]="!name.trim() || busy()">{{ busy() ? 'Saving…' : 'Create plan' }}</button>
    </div>

    <div class="card">
      <div class="head">
        <h3>Plans</h3>
        <span class="search"><input placeholder="Search plans…" [(ngModel)]="planSearch" (keyup.enter)="load()" />
          <button class="ghost" (click)="load()">Search</button></span>
      </div>
      <div class="plan" *ngFor="let p of plans()">
        <div class="plan-head">
          <div>
            <strong>{{ p.name }}</strong>
            <span [class.ok]="p.status === 'active'" [class.muted]="p.status !== 'active'"> · {{ p.status }}</span>
            <div class="muted small">{{ p.description }}</div>
            <div class="chips">
              <span class="chip mono" *ngFor="let s of p.stacks">{{ s.stack }} · {{ s.monthly_cost | currency }}</span>
            </div>
          </div>
          <button class="ghost" (click)="openReport(p)">Customers</button>
        </div>

        <div class="report" *ngIf="reportFor() === p.id">
          <div class="assign">
            <input placeholder="customer id" [(ngModel)]="assignId" />
            <input placeholder="customer email" [(ngModel)]="assignEmail" />
            <button class="ghost" (click)="assign(p)" [disabled]="!assignId.trim()">Assign customer</button>
            <span class="search"><input placeholder="filter customers…" [(ngModel)]="custSearch" (keyup.enter)="openReport(p)" />
              <button class="ghost" (click)="openReport(p)">Filter</button></span>
          </div>
          <table *ngIf="customers().length; else nocust">
            <thead><tr><th>Customer</th><th>Email</th><th>Status</th></tr></thead>
            <tbody>
              <tr *ngFor="let c of customers()">
                <td class="mono">{{ c.customer_id }}</td><td>{{ c.customer_email || '—' }}</td><td class="ok">{{ c.status }}</td>
              </tr>
            </tbody>
          </table>
          <ng-template #nocust><p class="muted">No customers on this plan yet.</p></ng-template>
        </div>
      </div>
      <p class="muted" *ngIf="plans().length === 0">No plans yet.</p>
    </div>
  `,
  styles: [
    `
      .create { margin-bottom: 16px; }
      .head, .plan-head { display: flex; justify-content: space-between; align-items: flex-start; }
      .search { display: inline-flex; gap: 8px; }
      .stacks { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px 16px; }
      .stack { display: flex; align-items: center; gap: 8px; font-weight: 500; }
      .cost { width: 90px; }
      .plan { border-top: 1px solid var(--border); padding: 12px 0; }
      .chips { margin-top: 6px; display: flex; gap: 8px; flex-wrap: wrap; }
      .chip { background: var(--panel-2); border-radius: 999px; padding: 2px 10px; font-size: 12px; }
      .mono { font-family: monospace; font-size: 12px; }
      .small { font-size: 12px; }
      .report { margin-top: 10px; padding: 10px; background: var(--panel-2); border-radius: 10px; }
      .assign { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
    `,
  ],
})
export class SubscriptionsComponent {
  private api = inject(ApiService);
  stacks = signal<string[]>([]);
  plans = signal<Plan[]>([]);
  customers = signal<SubscriptionRow[]>([]);
  reportFor = signal<string | null>(null);
  busy = signal(false);
  error = signal('');

  name = '';
  description = '';
  picks = new Set<string>();
  cost: Record<string, number> = {};
  planSearch = '';
  assignId = '';
  assignEmail = '';
  custSearch = '';

  constructor() {
    this.api.techStacks().subscribe({ next: (s) => this.stacks.set(s), error: () => {} });
    this.load();
  }

  picked(s: string): boolean {
    return this.picks.has(s);
  }
  toggle(s: string): void {
    if (this.picks.has(s)) this.picks.delete(s);
    else this.picks.add(s);
  }

  load(): void {
    this.api.plans(this.planSearch.trim() || undefined).subscribe({
      next: (p) => this.plans.set(p),
      error: () => {},
    });
  }

  create(): void {
    this.error.set('');
    this.busy.set(true);
    const stacks = Array.from(this.picks).map((s) => ({ stack: s, monthly_cost: Number(this.cost[s] || 0) }));
    this.api.createPlan({ name: this.name.trim(), description: this.description, stacks }).subscribe({
      next: () => {
        this.busy.set(false);
        this.name = '';
        this.description = '';
        this.picks.clear();
        this.cost = {};
        this.load();
      },
      error: (err) => {
        this.busy.set(false);
        this.error.set(err?.error?.detail ?? 'Create failed');
      },
    });
  }

  openReport(p: Plan): void {
    this.reportFor.set(p.id);
    this.api.planCustomers(p.id, this.custSearch.trim() || undefined).subscribe({
      next: (rows) => this.customers.set(rows),
      error: () => this.customers.set([]),
    });
  }

  assign(p: Plan): void {
    if (!this.assignId.trim()) return;
    this.api
      .assignCustomer(p.id, { customer_id: this.assignId.trim(), customer_email: this.assignEmail.trim() || undefined })
      .subscribe({
        next: () => {
          this.assignId = '';
          this.assignEmail = '';
          this.openReport(p);
        },
        error: () => {},
      });
  }
}
