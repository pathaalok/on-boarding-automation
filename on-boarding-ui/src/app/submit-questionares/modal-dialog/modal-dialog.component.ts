import { CommonModule } from "@angular/common";
import { CUSTOM_ELEMENTS_SCHEMA, Component, Inject } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MAT_DIALOG_DATA, MatDialogModule } from "@angular/material/dialog";
import { DomSanitizer, SafeHtml } from "@angular/platform-browser";

@Component({
    selector: 'app-confirm-dialog',
    imports: [
        CommonModule,
        MatDialogModule,
        MatButtonModule
      ],
    schemas: [CUSTOM_ELEMENTS_SCHEMA],
    template: `
               
              <mat-dialog-content style="padding: 0; overflow: hidden; height: 75vh; width: 75vw;">
  <!-- Close button -->
  <div style="display: flex; justify-content: flex-end; padding: 8px 12px;">
    <button mat-button color="warn" [mat-dialog-close]="true">✕</button>
  </div>

  <!-- Iframe wrapper for sizing -->
  <div style="height: calc(100% - 48px);"> <!-- Adjust for button height -->
    <iframe 
      [srcdoc]="sanitizedHtml"
      style="
        width: 100%; 
        height: 100%; 
        border: none; 
        border-radius: 10px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); 
        overflow: auto;">
    </iframe>
  </div>
</mat-dialog-content>

              `
  })
  export class ConfirmDialogComponent {
    sanitizedHtml: SafeHtml;
    constructor(@Inject(MAT_DIALOG_DATA) public data: any,private sanitizer: DomSanitizer) {
        this.sanitizedHtml = this.sanitizer.bypassSecurityTrustHtml(data.event);
    }
  }