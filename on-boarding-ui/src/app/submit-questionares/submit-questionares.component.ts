import { CUSTOM_ELEMENTS_SCHEMA, Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatStepperModule } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { EventStreamService } from './event-stream.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatExpansionModule } from '@angular/material/expansion';
import { SubmitQuestionareComponent } from '../submit-questionare/submit-questionare.component';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { ConfirmDialogComponent } from './modal-dialog/modal-dialog.component';

interface QuestionData {
  questions: string[];
  answers: { [index: string]: string };
}

@Component({
  selector: 'app-submit-questionares',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatStepperModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatExpansionModule,
    MatDialogModule,
    SubmitQuestionareComponent
  ],
  templateUrl: './submit-questionares.component.html',
  styleUrls: ['./submit-questionares.component.scss'],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
})
export class SubmitQuestionaresComponent implements OnInit {
  private _snackBar = inject(MatSnackBar);

  allQuestionares: Record<string, QuestionData> = {};
  questionareFormState = "Disable";

  constructor(private http: HttpClient,public eventStreamService: EventStreamService) {}

  ngOnInit(): void {
    this.eventStreamService.getServerEvents().subscribe({
      next: (msg:any) => this.eventStreamService.events.push(msg),
      error: (err) => console.error('SSE error:', err),
    });

    this.loadQuestionaresToSubmit();
  }

  loadQuestionaresToSubmit() {
    this.http.get('http://localhost:8000/all_submit_qa').subscribe((res:any) => {
      this.allQuestionares = res;
    });
  }

  onPanelOpened(questionare:any){
    
  }

  onPanelClosed(questionare:any){
  }
  

  openSnackBar(message: string, action: string) {
    this._snackBar.open(message,action,{
      duration: 5000
    });
  }

  formSubmit(event:any){
    this.http.delete('http://localhost:8000/submit_qa/'+event.key).subscribe((res:any) => {
      this.allQuestionares = res;
    });
  }

}
