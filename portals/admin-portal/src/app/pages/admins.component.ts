import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api.service';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-admins',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h2 class="page-title">Admins</h2>
    <p class="muted">Superadmin-only: manage admin accounts and their roles.</p>

    <div class="card create">
      <div class="row">
        <input placeholder="email" [(ngModel)]="email" />
        <input placeholder="password" type="password" [(ngModel)]="password" />
        <select [(ngModel)]="role">
          <option value="viewer">viewer</option>
          <option value="admin">admin</option>
          <option value="superadmin">superadmin</option>
        </select>
        <button (click)="create()" [disabled]="!email || !password || busy()">Create</button>
      </div>
      <p class="error" *ngIf="error()">{{ error() }}</p>
    </div>

    <div class="card">
      <table>
        <thead><tr><th>Email</th><th>Role</th><th></th></tr></thead>
        <tbody>
          <tr *ngFor="let a of admins()">
            <td>{{ a.email }}</td>
            <td>
              <select [ngModel]="a.role" (ngModelChange)="changeRole(a, $event)" [disabled]="a.email === auth.email()">
                <option value="viewer">viewer</option>
                <option value="admin">admin</option>
                <option value="superadmin">superadmin</option>
              </select>
            </td>
            <td>
              <button class="ghost" (click)="unlock(a)">Unlock</button>
              <button class="ghost" (click)="remove(a)" [disabled]="a.email === auth.email()">
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  `,
  styles: [
    `
      .create { margin-bottom: 16px; }
      .row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
      .row input, .row select { max-width: 220px; }
    `,
  ],
})
export class AdminsComponent {
  private api = inject(ApiService);
  auth = inject(AuthService);

  admins = signal<any[]>([]);
  email = '';
  password = '';
  role = 'viewer';
  busy = signal(false);
  error = signal('');

  constructor() {
    this.load();
  }

  load(): void {
    this.api.admins().subscribe({ next: (a) => this.admins.set(a), error: () => {} });
  }

  create(): void {
    this.error.set('');
    this.busy.set(true);
    this.api.createAdmin({ email: this.email, password: this.password, role: this.role }).subscribe({
      next: () => {
        this.email = '';
        this.password = '';
        this.busy.set(false);
        this.load();
      },
      error: (err) => {
        this.busy.set(false);
        this.error.set(err?.error?.detail ?? 'Create failed');
      },
    });
  }

  changeRole(a: any, role: string): void {
    this.api.updateAdmin(a.id, { role }).subscribe({ next: () => this.load(), error: () => this.load() });
  }

  remove(a: any): void {
    this.api.deleteAdmin(a.id).subscribe({ next: () => this.load(), error: () => {} });
  }

  unlock(a: any): void {
    this.api.unlockAdmin(a.id).subscribe({ next: () => {}, error: () => {} });
  }
}
