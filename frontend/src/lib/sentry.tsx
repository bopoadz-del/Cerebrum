import * as Sentry from '@sentry/react';
import { BrowserTracing } from '@sentry/tracing';
import React from 'react';

// Sentry configuration
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN;
const ENVIRONMENT = import.meta.env.VITE_APP_ENV || 'development';
const RELEASE = import.meta.env.VITE_APP_VERSION || '1.0.0';

// Initialize Sentry
export const initSentry = (): void => {
  if (!SENTRY_DSN) {
    console.warn('Sentry DSN not configured. Error tracking disabled.');
    return;
  }

  Sentry.init({
    dsn: SENTRY_DSN,
    environment: ENVIRONMENT,
    release: RELEASE,
    integrations: [
      new BrowserTracing({
        // Trace all requests to API
        tracePropagationTargets: [
          /^https:\/\/api\.cerebrum\.ai/,
          /^https:\/\/.*\.cerebrum\.ai/,
          /localhost/,
        ],
      }),
    ],
    // Performance monitoring
    tracesSampleRate: ENVIRONMENT === 'production' ? 0.1 : 1.0,
    // Error sampling
    sampleRate: 1.0,
    // Session replay
    replaysSessionSampleRate: ENVIRONMENT === 'production' ? 0.01 : 0.1,
    replaysOnErrorSampleRate: 1.0,
    // Before send filter
    beforeSend(event) {
      // Filter out specific errors
      if (shouldIgnoreError(event)) {
        return null;
      }
      return event;
    },
    // Ignore certain errors
    ignoreErrors: [
      // Browser extensions
      /chrome-extension/,
      /moz-extension/,
      // Network errors
      'Network Error',
      'Failed to fetch',
      'AbortError',
      // Common non-actionable errors
      'ResizeObserver loop limit exceeded',
      'Non-Error promise rejection captured',
    ],
    // Deny URLs
    denyUrls: [
      // Browser extensions
      /extensions\//i,
      /^chrome:\/\//i,
      /^chrome-extension:\/\//i,
      /^moz-extension:\/\//i,
    ],
  });
};

// Check if error should be ignored
const shouldIgnoreError = (event: Sentry.Event): boolean => {
  const errorMessage = event.exception?.values?.[0]?.value || '';

  // Ignore specific error patterns
  const ignoredPatterns = [
    /ResizeObserver loop/,
    /Network request failed/,
    /Failed to fetch/,
  ];

  return ignoredPatterns.some((pattern) => pattern.test(errorMessage));
};

// Set user context
export const setSentryUser = (user: {
  id: string;
  email?: string;
  username?: string;
  [key: string]: unknown;
}): void => {
  Sentry.setUser(user);
};

// Clear user context
export const clearSentryUser = (): void => {
  Sentry.setUser(null);
};

// Set tags
export const setSentryTag = (key: string, value: string): void => {
  Sentry.setTag(key, value);
};

// Set extra context
export const setSentryContext = (name: string, context: Record<string, unknown>): void => {
  Sentry.setContext(name, context);
};

// Capture exception
export const captureException = (
  error: Error,
  context?: Record<string, unknown>
): string => {
  if (context) {
    Sentry.withScope((scope) => {
      Object.entries(context).forEach(([key, value]) => {
        scope.setExtra(key, value);
      });
      Sentry.captureException(error);
    });
  } else {
    Sentry.captureException(error);
  }

  return Sentry.lastEventId() || '';
};

// Capture message
export const captureMessage = (
  message: string,
  level: Sentry.SeverityLevel = 'info'
): string => {
  Sentry.captureMessage(message, level);
  return Sentry.lastEventId() || '';
};

// Add breadcrumb
export const addBreadcrumb = (breadcrumb: Sentry.Breadcrumb): void => {
  Sentry.addBreadcrumb(breadcrumb);
};

// Performance monitoring
export const startTransaction = (
  name: string,
  op: string
): Sentry.Transaction => {
  return Sentry.startTransaction({ name, op });
};

// Custom error boundary fallback
export const SentryErrorBoundaryFallback: React.FC<{
  error: Error;
  componentStack: string | null;
  eventId: string | null;
  resetError: () => void;
}> = ({ error, componentStack, eventId, resetError }) => (
  <div className="min-h-screen flex items-center justify-center p-6 bg-gray-50 dark:bg-gray-950">
    <div className="max-w-lg w-full bg-white dark:bg-gray-900 rounded-xl shadow-lg border border-gray-200 dark:border-gray-800 p-8 text-center">
      <div className="w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mx-auto mb-6">
        <svg
          className="w-8 h-8 text-red-600 dark:text-red-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      </div>

      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
        Something went wrong
      </h2>

      <p className="text-gray-600 dark:text-gray-400 mb-4">
        We've been notified and are working to fix the issue.
      </p>

      {eventId && (
        <p className="text-sm text-gray-500 dark:text-gray-500 mb-6">
          Error ID: <code className="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">{eventId}</code>
        </p>
      )}

      {process.env.NODE_ENV === 'development' && (
        <details className="mb-6 text-left">
          <summary className="text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
            Error Details
          </summary>
          <pre className="mt-2 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs text-gray-700 dark:text-gray-300 overflow-auto max-h-48">
            {error.toString()}
            {'\n'}
            {componentStack}
          </pre>
        </details>
      )}

      <button
        onClick={resetError}
        className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
      >
        Try Again
      </button>
    </div>
  </div>
);

// Export Sentry for direct access
export { Sentry };

export default {
  initSentry,
  setSentryUser,
  clearSentryUser,
  setSentryTag,
  setSentryContext,
  captureException,
  captureMessage,
  addBreadcrumb,
  startTransaction,
  SentryErrorBoundaryFallback,
};
