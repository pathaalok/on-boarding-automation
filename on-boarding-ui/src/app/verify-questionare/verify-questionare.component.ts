import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatStepperModule } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatExpansionModule } from '@angular/material/expansion';


interface QuestionData {
  questions: string[];
  answers: { [index: string]: string };
}

@Component({
  selector: 'app-on-board-questionare',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatStepperModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatExpansionModule,
  ],
  templateUrl: './verify-questionare.component.html',
  styleUrls: ['./verify-questionare.component.scss'],
})
export class VerifyQuestionareComponent implements OnInit {

 
  private _snackBar = inject(MatSnackBar);

  allQuestionares: Record<string, QuestionData> = {};

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    this.loadQuestionaresToVerify();
  }

  loadQuestionaresToVerify() {
    this.http.get('http://localhost:8000/all_verify_qa').subscribe((res:any) => {
      this.allQuestionares = res;
    });
  }

  verifyDataConflicts(questionId: string) {
    const session = this.allQuestionares[questionId];
    alert(`Verified session: ${questionId}`);
  }

  proceedToSubmit(questionId: string){
    let payload = this.allQuestionares[questionId]
    this.http.post<any>('http://localhost:8000/store_submit_qa', payload).subscribe(res => {
      this.deleteQuestionare(questionId);
    });
  }

  deleteQuestionare(questionId: string) {
    this.http.delete('http://localhost:8000/verify_qa/'+questionId).subscribe((res:any) => {
      this.allQuestionares = res;
      this.openSnackBar("Action successfully processed","");
    });
  }

  openSnackBar(message: string, action: string) {
    this._snackBar.open(message,action,{
      duration: 5000
    });
  }

}
