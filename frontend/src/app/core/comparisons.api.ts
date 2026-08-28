import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { Comparison, MatchKind, MatchRow } from './models';

@Injectable({ providedIn: 'root' })
export class ComparisonsApi {
  private readonly http = inject(HttpClient);

  list(): Observable<Comparison[]> {
    return this.http.get<Comparison[]>('/api/comparisons');
  }

  get(id: number): Observable<Comparison> {
    return this.http.get<Comparison>(`/api/comparisons/${id}`);
  }

  create(fileAId: number, fileBId: number, dateToleranceDays = 7): Observable<Comparison> {
    return this.http.post<Comparison>('/api/comparisons', {
      file_a_id: fileAId,
      file_b_id: fileBId,
      date_tolerance_days: dateToleranceDays,
    });
  }

  matches(id: number, kind?: MatchKind): Observable<MatchRow[]> {
    let params = new HttpParams();
    if (kind) {
      params = params.set('kind', kind);
    }
    return this.http.get<MatchRow[]>(`/api/comparisons/${id}/matches`, { params });
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`/api/comparisons/${id}`);
  }
}
