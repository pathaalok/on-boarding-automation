import { Routes } from '@angular/router';
import { SubmitQuestionareComponent } from './submit-questionare/submit-questionare.component';
import { VerifyQuestionareComponent } from './verify-questionare/verify-questionare.component';
import { OnBoardQuestionareComponent } from './on-board-questionare/on-board-questionare.component';

export const routes: Routes = [
    { path: 'on-board-questionare', component: OnBoardQuestionareComponent },
    { path: 'verify-questionare', component: VerifyQuestionareComponent },
  { path: 'submit-questionare', component: SubmitQuestionareComponent },
  { path: '**', redirectTo: 'on-board-questionare' } 
];
