import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, Customer } from '../core/api.service';

@Component({
  selector: 'app-customer-listing',
  standalone: true,
  imports: [CommonModule],
  template: `
    <h2 class="page-title">Customer Listing</h2>
    <div class="card">
      <table>
        <thead>
          <tr><th>Email</th><th>Name</th><th>Status</th><th>ID</th></tr>
        </thead>
        <tbody>
          <tr *ngFor="let c of customers()">
            <td>{{ c.email }}</td>
            <td>{{ c.name || '—' }}</td>
            <td>{{ c.status }}</td>
            <td class="muted mono">{{ c.id }}</td>
          </tr>
        </tbody>
      </table>
      <p class="muted" *ngIf="customers().length === 0">No customers yet.</p>
    </div>
  `,
  styles: [`.mono { font-family: monospace; font-size: 12px; }`],
})
export class CustomerListingComponent {
  private api = inject(ApiService);
  customers = signal<Customer[]>([]);

  constructor() {
    this.api.customers().subscribe({ next: (c) => this.customers.set(c), error: () => {} });
  }
}
