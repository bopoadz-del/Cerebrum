import React from 'react';
import { Toaster as HotToaster, toast as hotToast, ToastOptions } from 'react-hot-toast';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  X,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Toast types
export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'loading';

interface ToastProps {
  message: string;
  type?: ToastType;
  duration?: number;
  id?: string;
}

// Custom toast component
const CustomToast: React.FC<{
  t: {
    id: string;
    visible: boolean;
    message: string;
    type: ToastType;
  };
}> = ({ t }) => {
  const icons = {
    success: <CheckCircle className="w-5 h-5 text-green-500" />,
    error: <XCircle className="w-5 h-5 text-red-500" />,
    warning: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
    info: <Info className="w-5 h-5 text-blue-500" />,
    loading: <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />,
  };

  const styles = {
    success: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
    error: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
    warning: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
    info: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    loading: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
  };

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border min-w-[300px] max-w-md',
        'bg-white dark:bg-gray-900',
        styles[t.type],
        t.visible ? 'animate-enter' : 'animate-leave'
      )}
    >
      {icons[t.type]}
      <p className="flex-1 text-sm font-medium text-gray-900 dark:text-white">
        {t.message}
      </p>
      {t.type !== 'loading' && (
        <button
          onClick={() => hotToast.dismiss(t.id)}
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
};

// Toast provider component
export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <>
      {children}
      <HotToaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: 'transparent',
            boxShadow: 'none',
            padding: 0,
          },
        }}
      >
        {(t) => <CustomToast t={t as any} />}
      </HotToaster>
    </>
  );
};

// Toast utility functions
export const toast = {
  success: (message: string, options?: ToastOptions) =>
    hotToast.success(message, {
      ...options,
      icon: <CheckCircle className="w-5 h-5 text-green-500" />,
    }),

  error: (message: string, options?: ToastOptions) =>
    hotToast.error(message, {
      ...options,
      icon: <XCircle className="w-5 h-5 text-red-500" />,
      duration: 6000,
    }),

  warning: (message: string, options?: ToastOptions) =>
    hotToast(message, {
      ...options,
      icon: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
    }),

  info: (message: string, options?: ToastOptions) =>
    hotToast(message, {
      ...options,
      icon: <Info className="w-5 h-5 text-blue-500" />,
    }),

  loading: (message: string, options?: ToastOptions) =>
    hotToast.loading(message, {
      ...options,
      icon: <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />,
    }),

  dismiss: (toastId?: string) => hotToast.dismiss(toastId),

  promise: <T,>(
    promise: Promise<T>,
    messages: {
      loading: string;
      success: string | ((data: T) => string);
      error: string | ((error: Error) => string);
    },
    options?: ToastOptions
  ) =>
    hotToast.promise(
      promise,
      {
        loading: messages.loading,
        success: messages.success,
        error: messages.error,
      },
      options
    ),

  custom: (message: string, options?: ToastOptions & { type?: ToastType }) => {
    const { type = 'info', ...rest } = options || {};
    const icons = {
      success: <CheckCircle className="w-5 h-5 text-green-500" />,
      error: <XCircle className="w-5 h-5 text-red-500" />,
      warning: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
      info: <Info className="w-5 h-5 text-blue-500" />,
      loading: <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />,
    };
    return hotToast(message, { ...rest, icon: icons[type] });
  },
};

// Hook for using toast
export const useToast = () => {
  return toast;
};

// Toast container for custom positioning
export const ToastContainer: React.FC<{
  position?: 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';
  className?: string;
}> = ({ position = 'top-right', className }) => {
  const positionClasses = {
    'top-left': 'top-4 left-4',
    'top-center': 'top-4 left-1/2 -translate-x-1/2',
    'top-right': 'top-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
    'bottom-right': 'bottom-4 right-4',
  };

  return (
    <HotToaster
      position={position}
      containerClassName={cn(positionClasses[position], className)}
      toastOptions={{
        duration: 4000,
        style: {
          background: 'transparent',
          boxShadow: 'none',
          padding: 0,
        },
      }}
    >
      {(t) => <CustomToast t={t as any} />}
    </HotToaster>
  );
};

export default ToastProvider;
