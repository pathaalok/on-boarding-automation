import { Injectable, NgZone } from '@angular/core';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class EventStreamService {
  constructor(private ngZone: NgZone) {}

  getServerEvents(): Observable<string> {
    return new Observable<string>((observer) => {
      const eventSource = new EventSource('http://localhost:8000/events'); // Adjust if needed

      eventSource.onmessage = (event) => {
        this.ngZone.run(() => {
          observer.next(event.data);
        });
      };

      eventSource.onerror = (error) => {
        console.error('EventSource error:', error);
        observer.error(error);
        eventSource.close();
      };

      return () => eventSource.close();
    });
  }
}
