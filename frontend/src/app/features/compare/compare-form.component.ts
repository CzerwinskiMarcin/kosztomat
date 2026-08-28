import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { ComparisonsApi } from '../../core/comparisons.api';
import { FilesApi } from '../../core/files.api';
import { Comparison, SourceFile } from '../../core/models';
import { EmptyStateComponent } from '../../shared/empty-state.component';

@Component({
  selector: 'app-compare-form',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSnackBarModule,
    EmptyStateComponent,
  ],
  templateUrl: './compare-form.component.html',
  styleUrl: './compare-form.component.scss',
})
export class CompareFormComponent implements OnInit {
  private readonly filesApi = inject(FilesApi);
  private readonly comparisonsApi = inject(ComparisonsApi);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);

  readonly files = signal<SourceFile[]>([]);
  readonly history = signal<Comparison[]>([]);
  readonly running = signal(false);

  fileAId: number | null = null;
  fileBId: number | null = null;
  tolerance = 7;

  async ngOnInit(): Promise<void> {
    const [files, history] = await Promise.all([
      firstValueFrom(this.filesApi.list()),
      firstValueFrom(this.comparisonsApi.list()),
    ]);
    this.files.set(files.filter((item) => item.status === 'imported'));
    this.history.set(history);
  }

  async run(): Promise<void> {
    if (this.fileAId === null || this.fileBId === null) {
      this.snackBar.open('Wybierz dwa różne, zaimportowane pliki.', 'OK');
      return;
    }
    this.running.set(true);
    try {
      const result = await firstValueFrom(
        this.comparisonsApi.create(this.fileAId, this.fileBId, this.tolerance),
      );
      await this.router.navigate(['/compare', result.id]);
    } catch {
      this.snackBar.open('Nie udało się porównać plików. Oba muszą być zaimportowane.', 'OK');
    } finally {
      this.running.set(false);
    }
  }
}
