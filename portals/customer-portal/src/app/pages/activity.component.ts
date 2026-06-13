import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivityItem, ApiService } from '../core/api.service';

@Component({
  selector: 'app-activity',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h2 class="page-title">Account Activity</h2>
    <p class="muted">Recent security-relevant activity on your account.</p>
    <div class="card">
      <table *ngIf="items().length; else empty">
        <thead>
          <tr><th>When</th><th>Event</th><th>Details</th></tr>
        </thead>
        <tbody>
          <tr *ngFor="let a of items()">
            <td class="mono">{{ a.created_at | date: 'short' }}</td>
            <td>
              <span class="badge" [class.warn]="isWarn(a.action)">{{ label(a.action) }}</span>
            </td>
            <td class="muted">{{ a.target || '' }}</td>
          </tr>
        </tbody>
      </table>
      <ng-template #empty><p class="muted">No activity recorded yet.</p></ng-template>
    </div>
  `,
  styles: [
    `
      .mono { font-family: monospace; font-size: 12px; }
      .badge { padding: 2px 8px; border-radius: 999px; background: var(--panel-2); font-weight: 600; font-size: 12px; }
      .badge.warn { background: #fde8e8; color: #c0392b; }
    `,
  ],
})
export class ActivityComponent {
  private api = inject(ApiService);
  items = signal<ActivityItem[]>([]);

  private labels: Record<string, string> = {
    'customer.signup': 'Account created',
    'customer.login.success': 'Signed in',
    'customer.login.failure': 'Failed sign-in attempt',
    'customer.password_reset': 'Password reset',
    'customer.email_verified': 'Email verified',
    'customer.token_reuse_detected': 'Suspicious token reuse — sessions revoked',
    'connection.connect': 'Connected a drive',
    'connection.disconnect': 'Disconnected a drive',
  };

  constructor() {
    this.api.activity().subscribe({ next: (a) => this.items.set(a), error: () => {} });
  }

  label(action: string): string {
    return this.labels[action] ?? action;
  }

  isWarn(action: string): boolean {
    return action === 'customer.login.failure' || action === 'customer.token_reuse_detected';
  }
}
