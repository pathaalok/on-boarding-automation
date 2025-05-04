import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatStepperModule } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { EventStreamService } from './event-stream.service';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-wf-stepper',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatStepperModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule
  ],
  templateUrl: './wf-stepper.component.html',
  styleUrls: ['./wf-stepper.component.scss'],
})
export class WfStepperComponent implements OnInit {
  private _snackBar = inject(MatSnackBar);

  firstFormGroup!: FormGroup;
  secondFormGroup!: FormGroup;
  events:any = [];
  submitAction: boolean =false;

  constructor(private fb: FormBuilder,private http: HttpClient,private eventStreamService: EventStreamService) {}

  ngOnInit(): void {
    this.eventStreamService.getServerEvents().subscribe({
      next: (msg) => this.events.push(msg),
      error: (err) => console.error('SSE error:', err),
    });

    this.firstFormGroup = this.fb.group({
      partition: ['', Validators.required],
      sorCodes: ['', Validators.required],
      busUnit: ['', Validators.required],
      rccRules: ['', Validators.required],
    });

    this.secondFormGroup = this.fb.group({
      jiraNo:['', Validators.required],
      baseBranch: ['', Validators.required],
      newBranch: ['', Validators.required],
    });
  }

  generatePayload() {
    const questions = [
      'Partition',
      'Eligible SOR Codes (Example: ACCT/SOR,DEAL/SOR)',
      'BUS UNIT',
      'RCC RULES'
    ];
  
    const firstValues = this.firstFormGroup.value;
  
    const answers = {
      "0": firstValues.partition,
      "1": firstValues.sorCodes,
      "2": firstValues.busUnit,
      "3": firstValues.rccRules
    };
  
    const payload = {
      base_branch: this.secondFormGroup.value.baseBranch,
      new_branch: this.secondFormGroup.value.newBranch,
      jira_no: this.secondFormGroup.value.jiraNo,
      questions,
      answers
    };
  
    console.log('Final Payload:', payload);
    return payload;
  }
  


  submit(){
    this.submitAction = true;
    let payload = this.generatePayload();

    this.http.post('http://localhost:8000/questionare', payload).subscribe({
      next: (response) => {
        console.log('Success:', response);
        this.openSnackBar('Onboarding submitted successfully!','');
        this.events.push('Onboarding submitted successfully!');
        setTimeout(()=>{
          this.events = [];
        },7500)
        this.submitAction = false;
      },
      error: (error) => {
        this.submitAction = false;
        console.error('Error:', error);
        this.openSnackBar('Failed to submit onboarding.','');
        this.events.push('Failed to submit onboarding.');
      }
    });
    
  }

  openSnackBar(message: string, action: string) {
    this._snackBar.open(message,action,{
      duration: 5000
    });
  }


}
