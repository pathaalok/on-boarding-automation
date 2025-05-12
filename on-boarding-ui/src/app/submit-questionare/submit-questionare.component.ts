import { CUSTOM_ELEMENTS_SCHEMA, Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatStepperModule } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatSnackBar } from '@angular/material/snack-bar';
import { EventStreamService } from '../submit-questionares/event-stream.service';

@Component({
  selector: 'app-submit-questionare',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatStepperModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule
  ],
  templateUrl: './submit-questionare.component.html',
  styleUrls: ['./submit-questionare.component.scss'],
})
export class SubmitQuestionareComponent implements OnInit,OnChanges  {
  private _snackBar = inject(MatSnackBar);

  firstFormGroup: FormGroup;
  submitAction: boolean =false;

  @Input() questionare!:any;
  @Input() questionareFormState: any;
  @Input() showBranchDetails:any ;

  @Output() formSubmit = new EventEmitter<any>();


  questionToFormControlMap: { [key: string]: string } = {
    "0": "partition",
    "1": "sorCodes",
    "2": "busUnit",
    "3": "rccRules",
    "4": "samplingRuleRef",
    "5": "samplingId",
    "6": "samplingData"
  };

  constructor(private fb: FormBuilder,private http: HttpClient,public eventStreamService: EventStreamService) {
    this.firstFormGroup = this.fb.group({
      partition: ['', Validators.required],
      sorCodes: ['', Validators.required],
      busUnit: ['', Validators.required],
      rccRules: ['', Validators.required],
      samplingRuleRef: [''],
      samplingId: ['', Validators.required],
      samplingData: ['', Validators.required],
      jiraNo:[''],
      baseBranch: [''],
      newBranch: [''],
    });
  }


  ngOnChanges(changes: SimpleChanges): void {
    if (changes['questionare'] && this.questionare) {
      this.patchAnswersToForm(this.questionare.value.answers);
    }

    if (changes['questionareFormState'] && this.questionareFormState) {
      if("Enable" == this.questionareFormState){
        this.firstFormGroup.enable();
      }else{
        this.firstFormGroup.disable();
        ['newBranch', 'jiraNo', 'baseBranch'].forEach(controlName => {
          this.firstFormGroup.get(controlName)?.enable();
        });
      }
    }
  }

  patchAnswersToForm(answers: { [key: string]: string }) {
    for (const [index, value] of Object.entries(answers)) {
      const controlName = this.questionToFormControlMap[index];
      if (controlName && this.firstFormGroup.contains(controlName)) {
        this.firstFormGroup.get(controlName)?.setValue(value);
      }
    }
  }
  

  ngOnInit(): void {
    
  }

  generatePayload() {
    const questions = this.questionare.questions;
  
    const firstValues = this.firstFormGroup.getRawValue();
  
    const answers = {
      "0": firstValues.partition,
      "1": firstValues.sorCodes,
      "2": firstValues.busUnit,
      "3": firstValues.rccRules,
      "4": firstValues.samplingRuleRef,
      "5": firstValues.samplingId,
      "6": firstValues.samplingData
    };
  
    const payload = {
      base_branch: this.firstFormGroup.value.baseBranch,
      new_branch: this.firstFormGroup.value.newBranch,
      jira_no: this.firstFormGroup.value.jiraNo,
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
        this.eventStreamService.events.push('Onboarding submitted successfully!');
        this.formSubmit.emit({status:"Success",key:this.questionare.key})
        setTimeout(()=>{
          this.eventStreamService.events = [];
        },7500)
        this.submitAction = false;
      },
      error: (error) => {
        this.submitAction = false;
        console.error('Error:', error);
        this.openSnackBar('Failed to submit onboarding.','');
        this.eventStreamService.events.push('Failed to submit onboarding.');
      }
    });
    
  }

  openSnackBar(message: string, action: string) {
    this._snackBar.open(message,action,{
      duration: 5000
    });
  }


}
