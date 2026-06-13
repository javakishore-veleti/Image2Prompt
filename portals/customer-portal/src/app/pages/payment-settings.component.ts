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
      <p class="muted">Stripe integration is stubbed in this build. Current settings:</p>
      <pre>{{ settings() | json }}</pre>
    </div>
  `,
  styles: [`pre { background: var(--panel-2); padding: 14px; border-radius: 10px; overflow:auto; }`],
})
export class PaymentSettingsComponent {
  private api = inject(ApiService);
  settings = signal<any>({});

  constructor() {
    this.api.paymentSettings().subscribe({ next: (s) => this.settings.set(s), error: () => {} });
  }
}
