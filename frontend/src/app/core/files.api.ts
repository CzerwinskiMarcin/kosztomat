import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import {
  FileImportRequest,
  ImportResult,
  Preview,
  SourceFile,
  TransactionPage,
} from './models';

@Injectable({ providedIn: 'root' })
export class FilesApi {
  private readonly http = inject(HttpClient);

  list(): Observable<SourceFile[]> {
    return this.http.get<SourceFile[]>('/api/files');
  }

  get(id: number): Observable<SourceFile> {
    return this.http.get<SourceFile>(`/api/files/${id}`);
  }

  upload(file: File): Observable<SourceFile> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<SourceFile>('/api/files', form);
  }

  rename(id: number, displayName: string): Observable<SourceFile> {
    return this.http.patch<SourceFile>(`/api/files/${id}`, { display_name: displayName });
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`/api/files/${id}`);
  }

  preview(
    id: number,
    options: {
      encoding?: string;
      delimiter?: string;
      skip_rows?: number;
      has_header?: boolean;
    } = {},
  ): Observable<Preview> {
    let params = new HttpParams();
    if (options.encoding) {
      params = params.set('encoding', options.encoding);
    }
    if (options.delimiter) {
      params = params.set('delimiter', options.delimiter);
    }
    if (options.skip_rows !== undefined) {
      params = params.set('skip_rows', String(options.skip_rows));
    }
    if (options.has_header !== undefined) {
      params = params.set('has_header', String(options.has_header));
    }
    return this.http.get<Preview>(`/api/files/${id}/preview`, { params });
  }

  importFile(id: number, payload: FileImportRequest): Observable<ImportResult> {
    return this.http.post<ImportResult>(`/api/files/${id}/import`, payload);
  }

  transactions(
    id: number,
    offset = 0,
    limit = 50,
    q?: string,
  ): Observable<TransactionPage> {
    let params = new HttpParams().set('offset', offset).set('limit', limit);
    if (q) {
      params = params.set('q', q);
    }
    return this.http.get<TransactionPage>(`/api/files/${id}/transactions`, { params });
  }
}
