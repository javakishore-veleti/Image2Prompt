import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, Customer } from '../core/api.service';

@Component({
  selector: 'app-customer-search',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h2 class="page-title">Customer Search</h2>
    <div class="search-row">
      <input placeholder="Search by email or name…" [(ngModel)]="term" (keyup.enter)="search()" />
      <button (click)="search()">Search</button>
    </div>
    <div class="card" *ngIf="results() as rows">
      <table>
        <thead>
          <tr><th>Email</th><th>Name</th><th>Status</th><th>ID</th></tr>
        </thead>
        <tbody>
          <tr *ngFor="let c of rows">
            <td>{{ c.email }}</td>
            <td>{{ c.name || '—' }}</td>
            <td>{{ c.status }}</td>
            <td class="mono muted">{{ c.id }}</td>
          </tr>
        </tbody>
      </table>
      <p class="muted" *ngIf="searched() && rows.length === 0">No matches.</p>
    </div>
  `,
  styles: [
    `
      .search-row { display: flex; gap: 10px; margin-bottom: 18px; max-width: 520px; }
      .mono { font-family: monospace; font-size: 12px; }
    `,
  ],
})
export class CustomerSearchComponent {
  private api = inject(ApiService);
  term = '';
  searched = signal(false);
  results = signal<Customer[]>([]);

  search(): void {
    this.api.customers(this.term.trim() || undefined).subscribe({
      next: (c) => {
        this.results.set(c);
        this.searched.set(true);
      },
      error: () => {},
    });
  }
}
