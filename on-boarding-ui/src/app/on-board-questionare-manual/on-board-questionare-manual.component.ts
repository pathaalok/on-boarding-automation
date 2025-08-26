import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatStepperModule } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatSnackBar } from '@angular/material/snack-bar';
import { FileUploadComponent } from '../file-upload/file-upload.component';

@Component({
  selector: 'app-on-board-questionare-manual',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    ReactiveFormsModule,
    FileUploadComponent
  ],
  templateUrl: './on-board-questionare-manual.component.html',
  styleUrls: ['./on-board-questionare-manual.component.scss'],
})
export class  OnBoardQuestionareManualComponent implements OnInit {

  private _snackBar = inject(MatSnackBar);
  sessionId = '';
  messages: { role: string, text: string }[] = [];
  userInput = '';
  previewMode = false;
  previewAnswers: any[] = [];
  answerHistory: string[][] = [];
  editingIndex: number | null = null;
  finalJson: any = null;
  confirmed = false;
  startNewOnboarding = false;

  questions: string[] = [
    "Enter On Boarding Name",
    "Enter Partition ? (P0, P1, P2, P3, P4, P5)",
    "Enter Eligible SOR Codes ? (Example: ACCT/SOR,DEAL/SOR)",
    "Enter BUS UNIT",
    "Enter RCC RULES",
    "Enter Sampling Rule Ref",
    'Enter Sampling Id',
    'Enter Sampling Data'
  ];

  formGroup!: FormGroup ;

  constructor(private fb: FormBuilder,private http: HttpClient) {}

  ngOnInit() {
    const controlsConfig = this.questions.reduce((acc, _, i) => {
      acc['field' + i] = ['', Validators.required]; 
      return acc;
    }, {} as { [key: string]: any });
  
    this.formGroup = this.fb.group(controlsConfig);
  }

  onSubmit() {
    const answers: { [key: string]: string } = {};
    Object.keys(this.formGroup.controls).forEach((key, index) => {
      answers[index.toString()] = this.formGroup.get(key)?.value || '';
    });
  
    this.finalJson = {
      questions: this.questions,
      answers: answers
    };
  
    this.sendDataForVerification();
  }

  sendDataForVerification(){
    this.http.post<any>('http://localhost:8000/store_verify_qa', this.finalJson).subscribe(res => {
      this.confirmed = true;
      this.openSnackBar("Updated successfully","");
      this.formGroup.reset();
    });
  }


  openSnackBar(message: string, action: string) {
    this._snackBar.open(message,action,{
      duration: 5000
    });
  }

  // Side panel functionality
  showSidePanel = false;

  openSidePanel(): void {
    this.showSidePanel = true;
  }

  closeSidePanel(): void {
    this.showSidePanel = false;
  }

}

  
