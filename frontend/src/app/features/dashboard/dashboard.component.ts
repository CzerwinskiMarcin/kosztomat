import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { firstValueFrom } from 'rxjs';

import { ComparisonsApi } from '../../core/comparisons.api';
import { FilesApi } from '../../core/files.api';
import { Comparison, SourceFile } from '../../core/models';
import { EmptyStateComponent } from '../../shared/empty-state.component';

@Component({
  selector: 'app-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, MatButtonModule, EmptyStateComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  private readonly filesApi = inject(FilesApi);
  private readonly comparisonsApi = inject(ComparisonsApi);

  readonly files = signal<SourceFile[]>([]);
  readonly comparisons = signal<Comparison[]>([]);
  readonly loading = signal(true);

  async ngOnInit(): Promise<void> {
    const [files, comparisons] = await Promise.all([
      firstValueFrom(this.filesApi.list()),
      firstValueFrom(this.comparisonsApi.list()),
    ]);
    this.files.set(files.slice(0, 5));
    this.comparisons.set(comparisons.slice(0, 5));
    this.loading.set(false);
  }
}
