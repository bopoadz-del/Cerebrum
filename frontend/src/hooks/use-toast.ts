// Simple toast hook wrapper around sonner
import { toast as sonnerToast } from "sonner";

export function useToast() {
  return {
    toast: sonnerToast,
    dismiss: sonnerToast.dismiss,
    error: sonnerToast.error,
    success: sonnerToast.success,
    info: sonnerToast.info,
    warning: sonnerToast.warning,
  };
}

export { sonnerToast as toast };
