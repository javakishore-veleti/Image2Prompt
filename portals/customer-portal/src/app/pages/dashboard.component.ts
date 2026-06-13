import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, ProcRequest } from '../core/api.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h2 class="page-title">Generate a Reverse Prompt</h2>
    <div class="grid">
      <div class="card">
        <div class="field">
          <label>Image</label>
          <input type="file" accept="image/*" (change)="onFile($event)" />
        </div>
        <div class="preview" *ngIf="previewUrl()">
          <img [src]="previewUrl()" alt="preview" />
        </div>
        <div class="field">
          <label>Instruction</label>
          <textarea rows="3" [(ngModel)]="instruction"></textarea>
        </div>
        <div class="field" *ngIf="projects().length">
          <label>Project <span class="muted">(optional)</span></label>
          <select [(ngModel)]="projectId">
            <option value="">— none —</option>
            <option *ngFor="let p of projects()" [value]="p.id">{{ p.name }}</option>
          </select>
        </div>
        <div class="field" *ngIf="providers().length">
          <label>Providers <span class="muted">(optional — none = your defaults)</span></label>
          <div class="providers">
            <label class="chk" *ngFor="let p of providers()">
              <input type="checkbox" [checked]="selected.has(p.key)" (change)="toggle(p.key)" />
              {{ p.name }}
            </label>
          </div>
        </div>
        <p class="muted small">
          The offline <code>mock</code> provider works with no cloud credentials.
        </p>
        <p class="error" *ngIf="error()">{{ error() }}</p>
        <button (click)="generate()" [disabled]="!file || loading()">
          {{ loading() ? 'Generating…' : 'Generate Reverse Prompt' }}
        </button>
      </div>

      <div class="card" *ngIf="result() as r">
        <h3>
          {{ r.providers.length > 1 ? 'Comparison' : 'Result' }}
          <span class="muted">({{ r.providers.length }} provider{{ r.providers.length === 1 ? '' : 's' }} · {{ r.status }})</span>
        </h3>
        <div class="result-grid" [class.single]="r.providers.length === 1">
          <div *ngFor="let p of r.providers" class="provider-out">
            <div class="provider-head">
              <strong>{{ p.provider_key }}</strong>
              <span [class.ok]="p.status === 'success'" [class.error]="p.status !== 'success'">
                {{ p.status }}
              </span>
              <span class="muted" *ngIf="p.latency_ms != null">· {{ p.latency_ms }}ms</span>
            </div>
            <p *ngIf="p.output_text" class="output-box">{{ p.output_text }}</p>
            <p *ngIf="p.error" class="error small">{{ p.error.message || p.error.type }}</p>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
      @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
      .preview img { max-width: 100%; border-radius: 12px; margin-bottom: 14px; }
      .small { font-size: 12px; }
      .providers { display: flex; flex-wrap: wrap; gap: 8px 16px; }
      .chk { display: flex; align-items: center; gap: 6px; font-weight: 500; }
      .chk input { width: auto; }
      .result-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
      .result-grid.single { grid-template-columns: 1fr; }
      @media (max-width: 700px) { .result-grid { grid-template-columns: 1fr; } }
      .provider-out { border: 1px solid var(--border); border-radius: 12px; padding: 12px; }
      .provider-head { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
      .output-box {
        background: var(--panel-2);
        color: var(--text);
        border: 1px solid var(--border);
        border-left: 6px solid var(--brand);
        border-radius: 10px;
        padding: 14px;
        line-height: 1.5;
      }
      code { color: var(--brand); }
    `,
  ],
})
export class DashboardComponent {
  private api = inject(ApiService);

  file: File | null = null;
  instruction = 'Generate a detailed text-to-image prompt that could recreate this image.';
  previewUrl = signal<string | null>(null);
  loading = signal(false);
  error = signal('');
  result = signal<ProcRequest | null>(null);
  providers = signal<{ key: string; name: string }[]>([]);
  selected = new Set<string>();
  projects = signal<{ id: string; name: string }[]>([]);
  projectId = '';

  constructor() {
    this.api.availableProviders().subscribe({
      next: (p) => this.providers.set(p),
      error: () => {},
    });
    this.api.projects().subscribe({
      next: (p) => this.projects.set(p),
      error: () => {},
    });
  }

  toggle(key: string): void {
    if (this.selected.has(key)) {
      this.selected.delete(key);
    } else {
      this.selected.add(key);
    }
  }

  onFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.file = input.files?.[0] ?? null;
    this.previewUrl.set(this.file ? URL.createObjectURL(this.file) : null);
  }

  generate(): void {
    if (!this.file) return;
    this.error.set('');
    this.loading.set(true);
    this.result.set(null);
    const providers = this.selected.size ? Array.from(this.selected).join(',') : undefined;
    this.api.generate(this.file, this.instruction, providers, this.projectId || undefined).subscribe({
      next: (res) => {
        this.result.set(res);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(err?.error?.detail ?? 'Generation failed');
        this.loading.set(false);
      },
    });
  }
}
