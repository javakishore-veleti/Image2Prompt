import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="auth-wrap">
      <div class="card auth-card">
        <h1 class="brand">Image<span>2</span>Prompt</h1>
        <p class="muted">Reset your password</p>
        <form (ngSubmit)="submit()" *ngIf="!done()">
          <div class="field">
            <label>Email</label>
            <input type="email" name="email" [(ngModel)]="email" required />
          </div>
          <button type="submit" [disabled]="loading()">{{ loading() ? 'Sending…' : 'Send reset link' }}</button>
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
export class ForgotPasswordComponent {
  private auth = inject(AuthService);

  email = '';
  loading = signal(false);
  done = signal(false);
  message = signal('');

  submit(): void {
    this.loading.set(true);
    this.auth.forgotPassword(this.email).subscribe({
      next: (r) => {
        this.loading.set(false);
        this.done.set(true);
        this.message.set(r.message);
      },
      // Even on error we show the generic message — never reveal account existence.
      error: () => {
        this.loading.set(false);
        this.done.set(true);
        this.message.set('If that email is registered, a reset link has been sent.');
      },
    });
  }
}
