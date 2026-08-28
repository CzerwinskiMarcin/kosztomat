import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ProfilePayload, SourceProfile } from './models';

@Injectable({ providedIn: 'root' })
export class ProfilesApi {
  private readonly http = inject(HttpClient);

  list(): Observable<SourceProfile[]> {
    return this.http.get<SourceProfile[]>('/api/profiles');
  }

  get(id: number): Observable<SourceProfile> {
    return this.http.get<SourceProfile>(`/api/profiles/${id}`);
  }

  create(payload: ProfilePayload): Observable<SourceProfile> {
    return this.http.post<SourceProfile>('/api/profiles', payload);
  }

  update(id: number, payload: ProfilePayload): Observable<SourceProfile> {
    return this.http.put<SourceProfile>(`/api/profiles/${id}`, payload);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`/api/profiles/${id}`);
  }
}
