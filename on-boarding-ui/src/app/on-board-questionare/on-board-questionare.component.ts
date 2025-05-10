import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
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
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule
  ],
  templateUrl: './on-board-questionare.component.html',
  styleUrls: ['./on-board-questionare.component.scss'],
})
export class OnBoardQuestionareComponent implements OnInit {
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

  constructor(private http: HttpClient) {}

  ngOnInit() {
    
  }

  startSession() {
    this.http.post<any>('http://localhost:8000/start', {}).subscribe(res => {
      this.sessionId = res.session_id;
      this.messages = [{ role: 'bot', text: res.question }];
      this.userInput = '';
      this.previewMode = false;
      this.previewAnswers = [];
      this.answerHistory = [];
      this.editingIndex = null;
      this.finalJson = null;
      this.confirmed = false;
      this.startNewOnboarding = true;
    });
  }

  sendMessage() {
    const msg = this.userInput.trim();
    if (!msg) return;

    this.messages.push({ role: 'user', text: msg });
    this.userInput = '';

    const payload: any = {
      session_id: this.sessionId,
      message: msg
    };
    if (this.editingIndex !== null) {
      payload.edit_index = this.editingIndex;
    }

    this.http.post<any>('http://localhost:8000/message', payload).subscribe(res => {
      this.messages.push({ role: 'bot', text: res.response });
      if (res.preview) {
        this.previewMode = true;
        this.previewAnswers = res.preview;
        this.answerHistory = res.history;
        this.editingIndex = null;
        this.finalJson = res.json_output;
      }
      if (res.final_output) {
        this.finalJson = res.final_output;
        this.sendDataForVerification()
      }
    });
  }

  sendDataForVerification(){
    this.http.post<any>('http://localhost:8000/store_verify_qa', this.finalJson).subscribe(res => {
      this.confirmed = true;
    });
  }

  confirmAnswers() {
    this.sendMessageWithText('Yes, I confirm.');
    this.previewMode = false;
  }

  editAnswer(index: number) {
    const latestValid = this.answerHistory[index]?.slice(-1)[0] || '';
    this.userInput = latestValid;
    this.previewMode = false;
    this.editingIndex = index;
  }

  sendMessageWithText(text: string) {
    this.messages.push({ role: 'user', text });
    this.http.post<any>('http://localhost:8000/message', {
      session_id: this.sessionId,
      message: text
    }).subscribe(res => {
      this.messages.push({ role: 'bot', text: res.response });
      if (res.final_output) {
        this.finalJson = res.final_output;
        this.sendDataForVerification()
      }
    });
  }

  restartChat() {
    this.startSession();
  }


}

  
