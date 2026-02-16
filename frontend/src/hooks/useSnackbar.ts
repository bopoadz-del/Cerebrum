import { useCallback } from 'react';
import toast from 'react-hot-toast';

type SnackbarSeverity = 'success' | 'error' | 'warning' | 'info';

export const useSnackbar = () => {
  const showSnackbar = useCallback((message: string, severity: SnackbarSeverity = 'info') => {
    switch (severity) {
      case 'success':
        toast.success(message);
        break;
      case 'error':
        toast.error(message);
        break;
      case 'warning':
        toast(message, { icon: '⚠️' });
        break;
      default:
        toast(message);
    }
  }, []);

  return { showSnackbar };
};

export default useSnackbar;
