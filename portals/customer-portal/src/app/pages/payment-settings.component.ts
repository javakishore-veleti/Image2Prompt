import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../core/api.service';

@Component({
  selector: 'app-payment-settings',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h2 class="page-title">Payment Settings</h2>
    <div class="card">
      <p>
        Stripe:
        <strong [class.ok]="settings()?.stripe_configured" [class.muted]="!settings()?.stripe_configured">
          {{ settings()?.stripe_configured ? 'connected' : 'not configured' }}
        </strong>
      </p>
      <p class="muted" *ngIf="settings()?.stripe_customer_id">
        Stripe customer: <code>{{ settings()?.stripe_customer_id }}</code>
      </p>

      <button (click)="addPaymentMethod()" [disabled]="!settings()?.stripe_configured || busy()">
        {{ busy() ? 'Preparing…' : 'Add payment method' }}
      </button>
      <p class="muted small" *ngIf="!settings()?.stripe_configured">
        Set <code>STRIPE_API_KEY</code> on the service to enable billing.
      </p>
      <p class="ok small" *ngIf="clientSecret()">
        Setup intent ready (secret obtained). Card capture uses Stripe Elements (next step).
      </p>
      <p class="error" *ngIf="error()">{{ error() }}</p>
    </div>
  `,
  styles: [`.small { font-size: 12px; } code { color: var(--brand); }`],
})
export class PaymentSettingsComponent {
  private api = inject(ApiService);
  settings = signal<any>(null);
  clientSecret = signal<string | null>(null);
  busy = signal(false);
  error = signal('');

  constructor() {
    this.api.paymentSettings().subscribe({ next: (s) => this.settings.set(s), error: () => {} });
  }

  addPaymentMethod(): void {
    this.error.set('');
    this.busy.set(true);
    this.api.createSetupIntent().subscribe({
      next: (r) => {
        this.busy.set(false);
        this.clientSecret.set(r.client_secret);
      },
      error: (err) => {
        this.busy.set(false);
        this.error.set(err?.error?.detail ?? 'Could not start setup');
      },
    });
  }
}
