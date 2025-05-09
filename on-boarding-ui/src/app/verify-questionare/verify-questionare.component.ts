import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatStepperModule } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-on-board-questionare',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatStepperModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule
  ],
  templateUrl: './verify-questionare.component.html',
  styleUrls: ['./verify-questionare.component.scss'],
})
export class VerifyQuestionareComponent implements OnInit {
  private _snackBar = inject(MatSnackBar);


  constructor(private fb: FormBuilder,private http: HttpClient) {}

  ngOnInit(): void {
   
  }

  

}
