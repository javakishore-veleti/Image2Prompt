import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-signin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="auth-wrap">
      <div class="card auth-card">
        <h1 class="brand">Image<span>2</span>Prompt</h1>
        <p class="muted">Sign in to your account</p>
        <form (ngSubmit)="submit()">
          <div class="field">
            <label>Email</label>
            <input type="email" name="email" [(ngModel)]="email" required />
          </div>
          <div class="field">
            <label>Password</label>
            <input type="password" name="password" [(ngModel)]="password" required />
          </div>
          <p class="error" *ngIf="error()">{{ error() }}</p>
          <button type="submit" [disabled]="loading()">{{ loading() ? 'Signing in…' : 'Sign in' }}</button>
        </form>
        <p class="muted switch">No account? <a routerLink="/signup">Create one</a></p>
      </div>
    </div>
  `,
  styles: [
    `
      .auth-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; }
      .auth-card { width: 380px; }
      .brand { font-size: 26px; font-weight: 800; margin: 0; }
      .brand span { color: var(--brand); }
      .switch { margin-top: 16px; text-align: center; }
    `,
  ],
})
export class SigninComponent {
  private auth = inject(AuthService);
  private router = inject(Router);

  email = '';
  password = '';
  loading = signal(false);
  error = signal('');

  submit(): void {
    this.error.set('');
    this.loading.set(true);
    this.auth.login(this.email, this.password).subscribe({
      next: () => this.router.navigateByUrl('/dashboard'),
      error: (err) => {
        this.error.set(err?.error?.detail ?? 'Sign in failed');
        this.loading.set(false);
      },
    });
  }
}
