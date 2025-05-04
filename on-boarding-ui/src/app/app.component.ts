import { CUSTOM_ELEMENTS_SCHEMA, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { WfStepperComponent } from './wf-stepper/wf-stepper.component';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet,WfStepperComponent],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  title = 'on-boarding-ui';
}
