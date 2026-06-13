import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, Provider } from '../core/api.service';

@Component({
  selector: 'app-providers',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h2 class="page-title">Providers</h2>
    <p class="muted">
      Toggle which AI providers the platform may dispatch process requests to. Disabled
      providers are never invoked, regardless of customer preferences.
    </p>
    <div class="card">
      <table>
        <thead>
          <tr><th>Provider</th><th>Key</th><th>Category</th><th>Enabled</th><th></th></tr>
        </thead>
        <tbody>
          <tr *ngFor="let p of providers()">
            <td>{{ p.name }}</td>
            <td class="mono">{{ p.key }}</td>
            <td>{{ p.category }}</td>
            <td>
              <span [class.ok]="p.enabled" [class.muted]="!p.enabled">
                {{ p.enabled ? 'Enabled' : 'Disabled' }}
              </span>
            </td>
            <td>
              <button class="ghost" (click)="toggle(p)" [disabled]="busy() === p.id">
                {{ p.enabled ? 'Disable' : 'Enable' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  `,
  styles: [`.mono { font-family: monospace; font-size: 12px; }`],
})
export class ProvidersComponent {
  private api = inject(ApiService);
  providers = signal<Provider[]>([]);
  busy = signal<string | null>(null);

  constructor() {
    this.load();
  }

  load(): void {
    this.api.providers().subscribe({ next: (p) => this.providers.set(p), error: () => {} });
  }

  toggle(p: Provider): void {
    this.busy.set(p.id);
    this.api.updateProvider(p.id, { enabled: !p.enabled }).subscribe({
      next: () => {
        this.busy.set(null);
        this.load();
      },
      error: () => this.busy.set(null),
    });
  }
}
