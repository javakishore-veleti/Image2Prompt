import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, PromptItem } from '../core/api.service';

@Component({
  selector: 'app-prompts',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h2 class="page-title">Generated Prompts</h2>
    <div class="search-row">
      <input placeholder="Search prompts…" [(ngModel)]="search" (keyup.enter)="load()" />
      <button (click)="load()">Search</button>
    </div>
    <p class="muted" *ngIf="!loading() && prompts().length === 0">No prompts yet. Generate one from the Dashboard.</p>
    <div class="card prompt" *ngFor="let p of prompts()">
      <div class="prompt-head">
        <strong>{{ p.provider_key }}</strong>
        <span class="muted">{{ p.created_at | date: 'medium' }}</span>
      </div>
      <p class="output-box">{{ p.output_text }}</p>
    </div>
  `,
  styles: [
    `
      .search-row { display: flex; gap: 10px; margin-bottom: 18px; max-width: 520px; }
      .prompt { margin-bottom: 14px; }
      .prompt-head { display: flex; justify-content: space-between; margin-bottom: 8px; }
      .output-box {
        background: var(--panel-2);
        color: var(--text);
        border: 1px solid var(--border);
        border-left: 6px solid var(--brand);
        border-radius: 10px;
        padding: 14px;
        line-height: 1.5;
        margin: 0;
      }
    `,
  ],
})
export class PromptsComponent {
  private api = inject(ApiService);

  search = '';
  loading = signal(false);
  prompts = signal<PromptItem[]>([]);

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.prompts(this.search.trim() || undefined).subscribe({
      next: (items) => {
        this.prompts.set(items);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
