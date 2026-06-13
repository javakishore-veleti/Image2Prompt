import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../core/api.service';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h2 class="page-title">Dashboard</h2>
    <div class="stats">
      <div class="card stat"><div class="num">{{ a()?.customers ?? '—' }}</div><div class="muted">Customers</div></div>
      <div class="card stat"><div class="num">{{ totalRequests() }}</div><div class="muted">Requests</div></div>
      <div class="card stat"><div class="num">{{ a()?.providers_enabled ?? '—' }}/{{ a()?.providers_total ?? '—' }}</div><div class="muted">Providers enabled</div></div>
    </div>

    <div class="card" *ngIf="providers().length">
      <h3>Per-provider</h3>
      <table>
        <thead><tr><th>Provider</th><th>Calls</th><th>Success</th><th>Errors</th><th>Avg latency</th></tr></thead>
        <tbody>
          <tr *ngFor="let p of providers()">
            <td class="mono">{{ p.provider_key }}</td>
            <td>{{ p.count }}</td>
            <td class="ok">{{ p.success }}</td>
            <td [class.error]="p.error > 0">{{ p.error }}</td>
            <td>{{ p.avg_latency_ms != null ? p.avg_latency_ms + ' ms' : '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card" *ngIf="overTime().length">
      <h3>Requests over time</h3>
      <div class="bars">
        <div class="bar-row" *ngFor="let d of overTime()">
          <span class="date muted">{{ d.date }}</span>
          <span class="bar" [style.width.px]="barWidth(d.count)"></span>
          <span class="cnt">{{ d.count }}</span>
        </div>
      </div>
    </div>

    <p class="muted" *ngIf="loaded() && totalRequests() === 0">No processing requests yet.</p>
  `,
  styles: [
    `
      .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 18px; }
      .stat { text-align: center; }
      .num { font-size: 32px; font-weight: 800; color: var(--brand); }
      .card { margin-bottom: 16px; }
      h3 { margin: 0 0 12px; color: var(--heading); }
      .mono { font-family: monospace; font-size: 12px; }
      .bars { display: flex; flex-direction: column; gap: 6px; }
      .bar-row { display: flex; align-items: center; gap: 10px; }
      .date { width: 96px; font-size: 12px; }
      .bar { height: 14px; background: var(--brand); border-radius: 4px; min-width: 2px; }
      .cnt { font-size: 12px; }
    `,
  ],
})
export class DashboardComponent {
  private api = inject(ApiService);
  a = signal<any>(null);
  loaded = signal(false);

  providers = computed(() => this.a()?.image_stats?.providers ?? []);
  overTime = computed(() => this.a()?.image_stats?.over_time ?? []);
  totalRequests = computed(() => this.a()?.image_stats?.total_requests ?? 0);

  private maxCount = computed(() =>
    Math.max(1, ...this.overTime().map((d: any) => d.count)),
  );

  constructor() {
    this.api.analytics().subscribe({
      next: (a) => {
        this.a.set(a);
        this.loaded.set(true);
      },
      error: () => this.loaded.set(true),
    });
  }

  barWidth(count: number): number {
    return Math.round((count / this.maxCount()) * 260);
  }
}
