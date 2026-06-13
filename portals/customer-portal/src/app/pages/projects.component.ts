import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../core/api.service';

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h2 class="page-title">Projects</h2>
    <p class="muted" *ngIf="projects().length === 0">
      No projects yet. Project grouping for your prompts will live here.
    </p>
    <div class="card" *ngFor="let p of projects()">
      <strong>{{ p.name }}</strong>
      <div class="muted">{{ p.id }}</div>
    </div>
  `,
})
export class ProjectsComponent {
  private api = inject(ApiService);
  projects = signal<any[]>([]);

  constructor() {
    this.api.projects().subscribe({ next: (p) => this.projects.set(p), error: () => {} });
  }
}
