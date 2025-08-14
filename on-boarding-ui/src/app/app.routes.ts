import { Routes } from '@angular/router';
import { VerifyQuestionareComponent } from './verify-questionare/verify-questionare.component';
import { OnBoardQuestionareComponent } from './on-board-questionare/on-board-questionare.component';
import { SubmitQuestionaresComponent } from './submit-questionares/submit-questionares.component';
import { OnBoardQuestionareManualComponent } from './on-board-questionare-manual/on-board-questionare-manual.component';
import { FileUploadComponent } from './file-upload/file-upload.component';

export const routes: Routes = [
  { path: 'on-board-questionare', component: OnBoardQuestionareManualComponent },
  { path: 'on-board-questionare-agent', component: OnBoardQuestionareComponent },
  { path: 'verify-questionare', component: VerifyQuestionareComponent },
  { path: 'submit-questionare', component: SubmitQuestionaresComponent },
  { path: 'file-upload', component: FileUploadComponent },
  { path: '**', redirectTo: 'on-board-questionare' } 
];
