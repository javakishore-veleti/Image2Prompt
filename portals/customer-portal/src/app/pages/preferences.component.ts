import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { ApiService, Preferences } from '../core/api.service';

@Component({
  selector: 'app-preferences',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h2 class="page-title">Preferences</h2>
    <div class="card" *ngIf="loaded()">
      <div class="field">
        <label>Default providers <span class="muted">(none = all enabled providers run)</span></label>
        <div class="providers">
          <label class="chk" *ngFor="let p of providers()">
            <input type="checkbox" [checked]="selected.has(p.key)" (change)="toggle(p.key)" />
            {{ p.name }}
          </label>
          <span class="muted" *ngIf="!providers().length">No providers are enabled yet.</span>
        </div>
      </div>

      <div class="field">
        <label>Storage backend <span class="muted">(where your uploads are kept)</span></label>
        <select [(ngModel)]="storageBackend">
          <option value="local">Local (server filesystem)</option>
          <option value="s3">AWS S3</option>
          <option value="azure">Azure Blob Storage</option>
          <option value="gcp">Google Cloud Storage</option>
        </select>
        <p class="muted small">Cloud backends require the service to be configured with credentials.</p>
      </div>

      <p class="ok" *ngIf="saved()">Preferences saved.</p>
      <p class="error" *ngIf="error()">{{ error() }}</p>
      <button (click)="save()" [disabled]="saving()">{{ saving() ? 'Saving…' : 'Save preferences' }}</button>
    </div>
  `,
  styles: [
    `
      .providers { display: flex; flex-wrap: wrap; gap: 8px 16px; }
      .chk { display: flex; align-items: center; gap: 6px; font-weight: 500; }
      .chk input { width: auto; }
      .small { font-size: 12px; }
      select { max-width: 320px; }
    `,
  ],
})
export class PreferencesComponent {
  private api = inject(ApiService);

  loaded = signal(false);
  saving = signal(false);
  saved = signal(false);
  error = signal('');
  providers = signal<{ key: string; name: string }[]>([]);
  selected = new Set<string>();
  storageBackend = 'local';

  constructor() {
    forkJoin({ prefs: this.api.preferences(), providers: this.api.availableProviders() }).subscribe({
      next: ({ prefs, providers }) => {
        this.providers.set(providers);
        this.storageBackend = prefs.storage_backend || 'local';
        (prefs.default_provider_keys || []).forEach((k) => this.selected.add(k));
        this.loaded.set(true);
      },
      error: () => {
        this.error.set('Could not load preferences');
        this.loaded.set(true);
      },
    });
  }

  toggle(key: string): void {
    this.selected.has(key) ? this.selected.delete(key) : this.selected.add(key);
    this.saved.set(false);
  }

  save(): void {
    this.error.set('');
    this.saved.set(false);
    this.saving.set(true);
    const body: Partial<Preferences> = {
      default_provider_keys: Array.from(this.selected),
      storage_backend: this.storageBackend,
    };
    this.api.updatePreferences(body).subscribe({
      next: () => {
        this.saving.set(false);
        this.saved.set(true);
      },
      error: (err) => {
        this.saving.set(false);
        this.error.set(err?.error?.detail ?? 'Save failed');
      },
    });
  }
}
