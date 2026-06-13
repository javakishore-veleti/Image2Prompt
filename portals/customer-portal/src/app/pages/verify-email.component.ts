import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-verify-email',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="auth-wrap">
      <div class="card auth-card">
        <h1 class="brand">Image<span>2</span>Prompt</h1>
        <p class="muted" *ngIf="state() === 'pending'">Verifying your email…</p>
        <p class="ok" *ngIf="state() === 'ok'">{{ message() }}</p>
        <p class="error" *ngIf="state() === 'error'">{{ message() }}</p>
        <p class="muted switch"><a routerLink="/dashboard">Go to dashboard</a></p>
      </div>
    </div>
  `,
  styles: [
    `
      .auth-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; }
      .auth-card { width: 380px; text-align: center; }
      .brand { font-size: 26px; font-weight: 800; margin: 0; }
      .brand span { color: var(--brand); }
      .switch { margin-top: 16px; }
    `,
  ],
})
export class VerifyEmailComponent {
  private auth = inject(AuthService);
  private route = inject(ActivatedRoute);

  state = signal<'pending' | 'ok' | 'error'>('pending');
  message = signal('');

  constructor() {
    const token = this.route.snapshot.queryParamMap.get('token') ?? '';
    if (!token) {
      this.state.set('error');
      this.message.set('Missing verification token.');
      return;
    }
    this.auth.verifyEmail(token).subscribe({
      next: (r) => {
        this.state.set('ok');
        this.message.set(r.message || 'Email verified.');
      },
      error: (err) => {
        this.state.set('error');
        this.message.set(err?.error?.detail ?? 'This verification link is invalid or has expired.');
      },
    });
  }
}
