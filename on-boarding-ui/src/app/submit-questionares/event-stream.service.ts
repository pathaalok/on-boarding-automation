import { Injectable, NgZone } from '@angular/core';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class EventStreamService {
  constructor(private ngZone: NgZone) {}

  
  events:any = [];
  
  getServerEvents(): Observable<any> {
    return new Observable<any>((observer) => {
      const eventSource = new EventSource('http://localhost:8000/events'); // Adjust if needed

      eventSource.onmessage = (event) => {
        this.ngZone.run(() => {
          observer.next(JSON.parse(event.data.replace(/'/g, '"')));
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
