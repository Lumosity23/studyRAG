
// Types manquants temporaires
declare module 'react-dropzone' {
  export interface DropzoneOptions {
    accept?: Record<string, string[]>
    multiple?: boolean
    onDrop?: (acceptedFiles: File[], rejectedFiles: any[]) => void
  }
  
  export interface DropzoneState {
    getRootProps: () => any
    getInputProps: () => any
    isDragActive: boolean
    isDragAccept: boolean
    isDragReject: boolean
  }
  
  export function useDropzone(options?: DropzoneOptions): DropzoneState
}
