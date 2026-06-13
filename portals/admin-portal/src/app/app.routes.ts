import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';
import { ShellComponent } from './layout/shell.component';

export const routes: Routes = [
  { path: 'signin', loadComponent: () => import('./pages/signin.component').then((m) => m.SigninComponent) },
  {
    path: '',
    component: ShellComponent,
    canActivate: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      { path: 'dashboard', loadComponent: () => import('./pages/dashboard.component').then((m) => m.DashboardComponent) },
      { path: 'customers/search', loadComponent: () => import('./pages/customer-search.component').then((m) => m.CustomerSearchComponent) },
      { path: 'customers', loadComponent: () => import('./pages/customer-listing.component').then((m) => m.CustomerListingComponent) },
      { path: 'customers/endpoints', loadComponent: () => import('./pages/customer-endpoints.component').then((m) => m.CustomerEndpointsComponent) },
      { path: 'providers', loadComponent: () => import('./pages/providers.component').then((m) => m.ProvidersComponent) },
    ],
  },
  { path: '**', redirectTo: '' },
];
