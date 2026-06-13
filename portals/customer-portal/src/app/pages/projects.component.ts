import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api.service';

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h2 class="page-title">Projects</h2>
    <div class="card create">
      <div class="field">
        <label>New project</label>
        <div class="row">
          <input placeholder="Project name" [(ngModel)]="name" (keyup.enter)="create()" />
          <button (click)="create()" [disabled]="!name.trim() || creating()">
            {{ creating() ? 'Creating…' : 'Create' }}
          </button>
        </div>
        <p class="error" *ngIf="error()">{{ error() }}</p>
      </div>
    </div>

    <p class="muted" *ngIf="projects().length === 0">
      No projects yet. Create one, then pick it on the Dashboard when generating to
      group those prompts.
    </p>
    <div class="card project" *ngFor="let p of projects()">
      <strong>{{ p.name }}</strong>
      <div class="muted mono">{{ p.id }}</div>
    </div>
  `,
  styles: [
    `
      .create { margin-bottom: 18px; }
      .row { display: flex; gap: 10px; max-width: 520px; }
      .project { margin-bottom: 10px; }
      .mono { font-family: monospace; font-size: 12px; }
    `,
  ],
})
export class ProjectsComponent {
  private api = inject(ApiService);
  projects = signal<any[]>([]);
  name = '';
  creating = signal(false);
  error = signal('');

  constructor() {
    this.load();
  }

  load(): void {
    this.api.projects().subscribe({ next: (p) => this.projects.set(p), error: () => {} });
  }

  create(): void {
    if (!this.name.trim()) return;
    this.error.set('');
    this.creating.set(true);
    this.api.createProject(this.name.trim()).subscribe({
      next: () => {
        this.name = '';
        this.creating.set(false);
        this.load();
      },
      error: (err) => {
        this.creating.set(false);
        this.error.set(err?.error?.detail ?? 'Create failed');
      },
    });
  }
}
