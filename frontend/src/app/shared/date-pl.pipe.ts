import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'datePl' })
export class DatePlPipe implements PipeTransform {
  transform(value: string | null | undefined): string {
    if (!value) {
      return '—';
    }
    const [year, month, day] = value.slice(0, 10).split('-');
    if (!year || !month || !day) {
      return value;
    }
    return `${day}.${month}.${year}`;
  }
}
