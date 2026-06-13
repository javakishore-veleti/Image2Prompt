import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, Provider } from '../core/api.service';

@Component({
  selector: 'app-providers',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h2 class="page-title">Providers</h2>
    <p class="muted">
      Toggle which AI providers the platform may dispatch process requests to. Disabled
      providers are never invoked, regardless of customer preferences.
    </p>
    <div class="card">
      <table>
        <thead>
          <tr><th>Provider</th><th>Key</th><th>Category</th><th>Credentials</th><th>Enabled</th><th></th></tr>
        </thead>
        <tbody>
          <ng-container *ngFor="let p of providers()">
            <tr>
              <td>{{ p.name }}</td>
              <td class="mono">{{ p.key }}</td>
              <td>{{ p.category }}</td>
              <td>
                <span class="muted" *ngIf="!configKeys(p).length">—</span>
                <span class="cred mono" *ngFor="let k of configKeys(p)">
                  {{ k }}: {{ p.config[k] }}
                  <button class="x" title="Remove" (click)="removeCredential(p, k)" [disabled]="busy() === p.id">✕</button>
                </span>
                <button class="link" (click)="toggleEditor(p.id)">{{ editing() === p.id ? 'Cancel' : '+ Set / rotate' }}</button>
              </td>
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
            <tr *ngIf="editing() === p.id" class="editor-row">
              <td colspan="6">
                <form class="cred-form" (ngSubmit)="setCredential(p)" autocomplete="off">
                  <input name="credName" placeholder="name (e.g. api_key)" [(ngModel)]="credName" />
                  <input name="credValue" type="password" placeholder="new secret value"
                         [(ngModel)]="credValue" autocomplete="new-password" />
                  <button type="submit" [disabled]="!credName || !credValue || busy() === p.id">Save</button>
                  <span class="muted small">Write-only — the value is stored encrypted and never shown again.</span>
                </form>
              </td>
            </tr>
          </ng-container>
        </tbody>
      </table>
      <p class="muted small">Secret values are masked (••••••••); the real keys never leave the server.</p>
    </div>
  `,
  styles: [
    `
      .mono { font-family: monospace; font-size: 12px; }
      .small { font-size: 12px; }
      .cred { display: inline-block; margin-right: 12px; }
      .x { background: none; border: none; color: #b00; padding: 0 2px; cursor: pointer; box-shadow: none; }
      .link { background: none; border: none; color: var(--brand); padding: 0; font-weight: 600; box-shadow: none; }
      .editor-row td { background: var(--panel-2); }
      .cred-form { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
      .cred-form input { width: 220px; }
    `,
  ],
})
export class ProvidersComponent {
  private api = inject(ApiService);
  providers = signal<Provider[]>([]);
  busy = signal<string | null>(null);
  editing = signal<string | null>(null);
  credName = 'api_key';
  credValue = '';

  configKeys(p: Provider): string[] {
    return Object.keys(p.config ?? {});
  }

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

  toggleEditor(id: string): void {
    this.editing.set(this.editing() === id ? null : id);
    this.credName = 'api_key';
    this.credValue = '';
  }

  setCredential(p: Provider): void {
    if (!this.credName || !this.credValue) {
      return;
    }
    this.busy.set(p.id);
    // Patch-merge: only this key changes; others (and unedited secrets) are preserved.
    this.api.updateProvider(p.id, { config: { [this.credName]: this.credValue } }).subscribe({
      next: () => {
        this.busy.set(null);
        this.editing.set(null);
        this.credValue = '';
        this.load();
      },
      error: () => this.busy.set(null),
    });
  }

  removeCredential(p: Provider, key: string): void {
    this.busy.set(p.id);
    // null deletes the key server-side.
    this.api.updateProvider(p.id, { config: { [key]: null } as any }).subscribe({
      next: () => {
        this.busy.set(null);
        this.load();
      },
      error: () => this.busy.set(null),
    });
  }
}
