import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'files',
    loadComponent: () =>
      import('./features/files/files-list.component').then((m) => m.FilesListComponent),
  },
  {
    path: 'files/:id',
    loadComponent: () =>
      import('./features/files/file-detail.component').then((m) => m.FileDetailComponent),
  },
  {
    path: 'profiles',
    loadComponent: () =>
      import('./features/profiles/profiles.component').then((m) => m.ProfilesComponent),
  },
  {
    path: 'compare',
    loadComponent: () =>
      import('./features/compare/compare-form.component').then((m) => m.CompareFormComponent),
  },
  {
    path: 'compare/:id',
    loadComponent: () =>
      import('./features/compare/compare-result.component').then((m) => m.CompareResultComponent),
  },
  { path: '**', redirectTo: '' },
];
