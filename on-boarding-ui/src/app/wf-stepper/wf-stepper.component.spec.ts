import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WfStepperComponent } from './wf-stepper.component';

describe('WfStepperComponent', () => {
  let component: WfStepperComponent;
  let fixture: ComponentFixture<WfStepperComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WfStepperComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(WfStepperComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
