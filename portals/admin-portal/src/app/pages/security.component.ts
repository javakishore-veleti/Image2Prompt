import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, CspDashboard } from '../core/api.service';

@Component({
  selector: 'app-security',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h2 class="page-title">Security · CSP Violations</h2>
    <p class="muted">
      Content-Security-Policy violation reports sent by browsers (via the portals'
      report-to / report-uri endpoints) and forwarded by the gateway.
    </p>

    <div class="cards">
      <div class="card stat">
        <div class="num">{{ data()?.total ?? 0 }}</div>
        <div class="muted">total reports</div>
      </div>
      <div class="card">
        <h3>Top directives</h3>
        <p class="muted" *ngIf="!data()?.summary?.length">No violations recorded.</p>
        <div class="bar" *ngFor="let s of data()?.summary">
          <span class="mono">{{ s.directive }}</span>
          <span class="count">{{ s.count }}</span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="head">
        <h3>Recent reports</h3>
        <button class="ghost" (click)="load()" [disabled]="loading()">Refresh</button>
      </div>
      <table *ngIf="data()?.violations?.length; else empty">
        <thead>
          <tr><th>When</th><th>Directive</th><th>Blocked URI</th><th>Document</th></tr>
        </thead>
        <tbody>
          <tr *ngFor="let v of data()?.violations">
            <td class="mono">{{ v.created_at | date: 'short' }}</td>
            <td class="mono">{{ v.violated_directive || '—' }}</td>
            <td class="mono trunc">{{ v.blocked_uri || '—' }}</td>
            <td class="mono trunc">{{ v.document_uri || '—' }}</td>
          </tr>
        </tbody>
      </table>
      <ng-template #empty><p class="muted">No violations recorded yet.</p></ng-template>
    </div>
  `,
  styles: [
    `
      .cards { display: grid; grid-template-columns: 200px 1fr; gap: 16px; margin-bottom: 16px; }
      @media (max-width: 700px) { .cards { grid-template-columns: 1fr; } }
      .stat { text-align: center; }
      .num { font-size: 40px; font-weight: 800; color: var(--brand); }
      .mono { font-family: monospace; font-size: 12px; }
      .trunc { max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .bar { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid var(--border); }
      .count { font-weight: 700; color: var(--brand); }
      .head { display: flex; justify-content: space-between; align-items: center; }
    `,
  ],
})
export class SecurityComponent {
  private api = inject(ApiService);
  data = signal<CspDashboard | null>(null);
  loading = signal(false);

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.cspViolations().subscribe({
      next: (d) => {
        this.data.set(d);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
