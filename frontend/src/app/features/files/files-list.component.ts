import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { FilesApi } from '../../core/files.api';
import { SourceFile } from '../../core/models';
import { DropzoneComponent } from '../../shared/dropzone.component';
import { EmptyStateComponent } from '../../shared/empty-state.component';

@Component({
  selector: 'app-files-list',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    DatePipe,
    MatButtonModule,
    MatSnackBarModule,
    DropzoneComponent,
    EmptyStateComponent,
  ],
  templateUrl: './files-list.component.html',
  styleUrl: './files-list.component.scss',
})
export class FilesListComponent implements OnInit {
  private readonly filesApi = inject(FilesApi);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);

  readonly files = signal<SourceFile[]>([]);
  readonly uploading = signal(false);

  async ngOnInit(): Promise<void> {
    await this.reload();
  }

  async onFile(file: File): Promise<void> {
    this.uploading.set(true);
    try {
      const uploaded = await firstValueFrom(this.filesApi.upload(file));
      if (uploaded.duplicate_of_file_id) {
        this.snackBar.open('Ten sam plik był już wgrany wcześniej — zapisano kopię.', 'OK', {
          duration: 4000,
        });
      }
      await this.router.navigate(['/files', uploaded.id]);
    } catch {
      this.snackBar.open('Nie udało się wgrać pliku. Sprawdź format i rozmiar (max 10 MB).', 'OK');
    } finally {
      this.uploading.set(false);
    }
  }

  private async reload(): Promise<void> {
    this.files.set(await firstValueFrom(this.filesApi.list()));
  }
}
