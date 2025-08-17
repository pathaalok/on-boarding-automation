import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatListModule } from '@angular/material/list';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';

interface UploadedFile {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
}

interface ApiResponse {
  message: string;
  summary: {
    total_files: number;
    successful: number;
    failed: number;
  };
  results: Array<{
    fileName: string;
    fileSize: number;
    status: string;
    fileId?: string;
    processingResult?: any;
    error?: string;
  }>;
  successful_files: Array<{
    fileName: string;
    fileSize: number;
    status: string;
    fileId?: string;
    processingResult?: any;
  }>;
  failed_files: Array<{
    fileName: string;
    fileSize: number;
    status: string;
    error?: string;
  }>;
}

@Component({
  selector: 'app-file-upload',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatListModule,
    MatChipsModule,
    MatSnackBarModule,
    MatTooltipModule
  ],
  templateUrl: './file-upload.component.html',
  styleUrls: ['./file-upload.component.scss']
})
export class FileUploadComponent implements OnInit {
  uploadedFiles: UploadedFile[] = [];
  isDragOver = false;
  maxFileSize = 10 * 1024 * 1024; // 10MB
  allowedFileTypes = [
    'application/pdf'
  ];

  isSubmitting = false;
  submitProgress = 0;
  apiResponse: ApiResponse | null = null;
  showResults = false;

  constructor(
    private snackBar: MatSnackBar,
    private http: HttpClient
  ) {}

  ngOnInit(): void {}

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;

    const files = event.dataTransfer?.files;
    if (files) {
      this.handleFiles(Array.from(files));
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      this.handleFiles(Array.from(input.files));
    }
  }

  private handleFiles(files: File[]): void {
    files.forEach(file => {
      if (this.validateFile(file)) {
        const uploadedFile: UploadedFile = {
          file,
          progress: 0,
          status: 'pending'
        };
        this.uploadedFiles.push(uploadedFile);
        this.uploadFile(uploadedFile);
      }
    });
  }

  private validateFile(file: File): boolean {
    // Check file size
    if (file.size > this.maxFileSize) {
      this.showError(`File ${file.name} is too large. Maximum size is 10MB.`);
      return false;
    }

    // Check file type
    if (!this.allowedFileTypes.includes(file.type)) {
      this.showError(`File type ${file.type} is not allowed for ${file.name}.`);
      return false;
    }

    // Check if file already exists
    if (this.uploadedFiles.some(f => f.file.name === file.name)) {
      this.showError(`File ${file.name} is already uploaded.`);
      return false;
    }

    return true;
  }

  private uploadFile(uploadedFile: UploadedFile): void {
    uploadedFile.status = 'uploading';
    
    // Simulate file upload with progress
    const interval = setInterval(() => {
      uploadedFile.progress += Math.random() * 30;
      
      if (uploadedFile.progress >= 100) {
        uploadedFile.progress = 100;
        uploadedFile.status = 'completed';
        clearInterval(interval);
        this.showSuccess(`File ${uploadedFile.file.name} uploaded successfully!`);
      }
    }, 200);
  }

  removeFile(index: number): void {
    this.uploadedFiles.splice(index, 1);
  }

  retryUpload(uploadedFile: UploadedFile): void {
    uploadedFile.progress = 0;
    uploadedFile.status = 'pending';
    uploadedFile.error = undefined;
    this.uploadFile(uploadedFile);
  }

  private showError(message: string): void {
    this.snackBar.open(message, 'Close', {
      duration: 5000,
      panelClass: ['error-snackbar']
    });
  }

  private showSuccess(message: string): void {
    this.snackBar.open(message, 'Close', {
      duration: 3000,
      panelClass: ['success-snackbar']
    });
  }

  getFileIcon(fileType: string): string {
    if (fileType.includes('pdf')) return 'picture_as_pdf';
    if (fileType.includes('word') || fileType.includes('document')) return 'description';
    if (fileType.includes('image')) return 'image';
    if (fileType.includes('excel') || fileType.includes('spreadsheet')) return 'table_chart';
    if (fileType.includes('text')) return 'text_snippet';
    return 'insert_drive_file';
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  submitFiles(): void {
    if (this.uploadedFiles.length === 0) {
      this.showError('No files to submit. Please upload files first.');
      return;
    }

    const completedFiles = this.uploadedFiles.filter(f => f.status === 'completed');
    if (completedFiles.length === 0) {
      this.showError('No completed files to submit. Please wait for uploads to complete.');
      return;
    }

    this.isSubmitting = true;
    this.submitProgress = 0;

    // Create FormData with all completed files
    const formData = new FormData();
    completedFiles.forEach((uploadedFile, index) => {
      formData.append(`file${index}`, uploadedFile.file);
    });

    // Add metadata
    formData.append('totalFiles', completedFiles.length.toString());
    formData.append('uploadTimestamp', new Date().toISOString());

    // Make API call
    this.http.post('/api/upload-files', formData, {
      reportProgress: true,
      observe: 'events'
    }).subscribe({
      next: (event: HttpEvent<any>) => {
        if (event.type === HttpEventType.UploadProgress) {
          this.submitProgress = Math.round(100 * event.loaded / (event.total || 1));
        } else if (event.type === HttpEventType.Response) {
          this.submitProgress = 100;
          this.isSubmitting = false;
          
          // Handle API response
          this.apiResponse = event.body as ApiResponse;
          this.showResults = true;
          
          // Show success message with the response message
          this.showSuccess(this.apiResponse?.message || `Successfully submitted ${completedFiles.length} files!`);
          
          // Clear the uploaded files after successful submission
          this.uploadedFiles = [];
        }
      },
      error: (error) => {
        this.isSubmitting = false;
        this.submitProgress = 0;
        console.error('Error submitting files:', error);
        this.showError('Failed to submit files. Please try again.');
      }
    });
  }

  canSubmit(): boolean {
    return this.uploadedFiles.length > 0 && 
           this.uploadedFiles.some(f => f.status === 'completed') &&
           !this.isSubmitting;
  }

  getCompletedFilesCount(): number {
    return this.uploadedFiles.filter(f => f.status === 'completed').length;
  }

  clearResults(): void {
    this.apiResponse = null;
    this.showResults = false;
  }

  uploadNewFiles(): void {
    this.clearResults();
  }
} 