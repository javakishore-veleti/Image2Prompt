import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="auth-wrap">
      <div class="card auth-card">
        <h1 class="brand">Image<span>2</span>Prompt</h1>
        <p class="muted">Choose a new password</p>
        <form (ngSubmit)="submit()" *ngIf="!done()">
          <div class="field">
            <label>New password</label>
            <input type="password" name="pw" [(ngModel)]="password" required minlength="8" />
          </div>
          <p class="error" *ngIf="error()">{{ error() }}</p>
          <button type="submit" [disabled]="loading() || !token">
            {{ loading() ? 'Saving…' : 'Reset password' }}
          </button>
          <p class="error" *ngIf="!token">Missing or invalid reset link.</p>
        </form>
        <p class="ok" *ngIf="done()">{{ message() }}</p>
        <p class="muted switch"><a routerLink="/signin">Back to sign in</a></p>
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
export class ResetPasswordComponent {
  private auth = inject(AuthService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  token = this.route.snapshot.queryParamMap.get('token') ?? '';
  password = '';
  loading = signal(false);
  done = signal(false);
  message = signal('');
  error = signal('');

  submit(): void {
    if (!this.token) {
      return;
    }
    this.error.set('');
    this.loading.set(true);
    this.auth.resetPassword(this.token, this.password).subscribe({
      next: (r) => {
        this.loading.set(false);
        this.done.set(true);
        this.message.set(r.message);
        setTimeout(() => this.router.navigateByUrl('/signin'), 2000);
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err?.error?.detail ?? 'Could not reset password. The link may have expired.');
      },
    });
  }
}
