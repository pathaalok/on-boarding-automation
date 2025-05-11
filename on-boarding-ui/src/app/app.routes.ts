import { Routes } from '@angular/router';
import { VerifyQuestionareComponent } from './verify-questionare/verify-questionare.component';
import { OnBoardQuestionareComponent } from './on-board-questionare/on-board-questionare.component';
import { SubmitQuestionaresComponent } from './submit-questionares/submit-questionares.component';

export const routes: Routes = [
    { path: 'on-board-questionare', component: OnBoardQuestionareComponent },
    { path: 'verify-questionare', component: VerifyQuestionareComponent },
  { path: 'submit-questionare', component: SubmitQuestionaresComponent },
  { path: '**', redirectTo: 'on-board-questionare' } 
];
