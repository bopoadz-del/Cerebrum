import { useEffect, useCallback, useRef } from 'react';

// Keyboard key codes and common combinations
type KeyCode = string;
type ModifierKey = 'ctrl' | 'alt' | 'shift' | 'meta';

interface KeyboardShortcut {
  key: KeyCode;
  modifiers?: ModifierKey[];
  handler: (event: KeyboardEvent) => void;
  preventDefault?: boolean;
  stopPropagation?: boolean;
  enabled?: boolean;
}

/**
 * Hook to listen for keyboard events
 * @param shortcuts - Array of keyboard shortcuts to listen for
 * @param deps - Dependencies array for the effect
 */
export const useKeyboard = (
  shortcuts: KeyboardShortcut[],
  deps: React.DependencyList = []
) => {
  const shortcutsRef = useRef(shortcuts);
  shortcutsRef.current = shortcuts;

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      shortcutsRef.current.forEach((shortcut) => {
        if (shortcut.enabled === false) return;

        const { key, modifiers = [], handler, preventDefault = true, stopPropagation = false } = shortcut;

        // Check if key matches
        const keyMatches = event.key.toLowerCase() === key.toLowerCase() ||
          event.code === key;

        // Check if all modifiers match
        const modifiersMatch = modifiers.every((modifier) => {
          switch (modifier) {
            case 'ctrl':
              return event.ctrlKey;
            case 'alt':
              return event.altKey;
            case 'shift':
              return event.shiftKey;
            case 'meta':
              return event.metaKey;
            default:
              return false;
          }
        });

        // Check if no extra modifiers are pressed
        const noExtraModifiers = !['ctrl', 'alt', 'shift', 'meta'].some(
          (mod) =>
            !modifiers.includes(mod as ModifierKey) &&
            (event as KeyboardEvent)[`${mod}Key` as keyof KeyboardEvent]
        );

        if (keyMatches && modifiersMatch && noExtraModifiers) {
          if (preventDefault) {
            event.preventDefault();
          }
          if (stopPropagation) {
            event.stopPropagation();
          }
          handler(event);
        }
      });
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, deps);
};

/**
 * Hook for single key press detection
 * @param key - Key to listen for
 * @param handler - Callback when key is pressed
 * @param options - Additional options
 */
export const useKeyPress = (
  key: KeyCode,
  handler: (event: KeyboardEvent) => void,
  options: {
    modifiers?: ModifierKey[];
    preventDefault?: boolean;
    enabled?: boolean;
  } = {}
) => {
  const { modifiers = [], preventDefault = true, enabled = true } = options;

  useKeyboard(
    [
      {
        key,
        modifiers,
        handler,
        preventDefault,
        enabled,
      },
    ],
    [key, handler, enabled]
  );
};

/**
 * Hook for escape key press
 * @param handler - Callback when escape is pressed
 * @param enabled - Whether the shortcut is enabled
 */
export const useEscapeKey = (
  handler: () => void,
  enabled: boolean = true
) => {
  useKeyPress('Escape', handler, { enabled });
};

/**
 * Hook for enter key press
 * @param handler - Callback when enter is pressed
 * @param enabled - Whether the shortcut is enabled
 */
export const useEnterKey = (
  handler: () => void,
  enabled: boolean = true
) => {
  useKeyPress('Enter', handler, { enabled });
};

/**
 * Hook for keyboard navigation (arrow keys)
 * @param handlers - Object with handlers for each arrow key
 * @param enabled - Whether navigation is enabled
 */
export const useArrowNavigation = (
  handlers: {
    onUp?: () => void;
    onDown?: () => void;
    onLeft?: () => void;
    onRight?: () => void;
  },
  enabled: boolean = true
) => {
  useKeyboard(
    [
      {
        key: 'ArrowUp',
        handler: () => handlers.onUp?.(),
        enabled,
      },
      {
        key: 'ArrowDown',
        handler: () => handlers.onDown?.(),
        enabled,
      },
      {
        key: 'ArrowLeft',
        handler: () => handlers.onLeft?.(),
        enabled,
      },
      {
        key: 'ArrowRight',
        handler: () => handlers.onRight?.(),
        enabled,
      },
    ],
    [handlers, enabled]
  );
};

/**
 * Hook for focus management with keyboard
 * @param itemCount - Number of focusable items
 * @returns Current focused index and setters
 */
export const useKeyboardFocus = (itemCount: number, initialIndex: number = -1) => {
  const [focusedIndex, setFocusedIndex] = React.useState(initialIndex);

  const focusNext = useCallback(() => {
    setFocusedIndex((prev) => (prev + 1) % itemCount);
  }, [itemCount]);

  const focusPrevious = useCallback(() => {
    setFocusedIndex((prev) => (prev - 1 + itemCount) % itemCount);
  }, [itemCount]);

  const focusFirst = useCallback(() => {
    setFocusedIndex(0);
  }, []);

  const focusLast = useCallback(() => {
    setFocusedIndex(itemCount - 1);
  }, [itemCount]);

  const clearFocus = useCallback(() => {
    setFocusedIndex(-1);
  }, []);

  useArrowNavigation(
    {
      onDown: focusNext,
      onUp: focusPrevious,
    },
    focusedIndex >= 0
  );

  return {
    focusedIndex,
    setFocusedIndex,
    focusNext,
    focusPrevious,
    focusFirst,
    focusLast,
    clearFocus,
  };
};

/**
 * Hook for global shortcuts
 * Common application shortcuts
 */
export const useGlobalShortcuts = (
  handlers: {
    onSearch?: () => void;
    onNew?: () => void;
    onSave?: () => void;
    onClose?: () => void;
    onHelp?: () => void;
  },
  enabled: boolean = true
) => {
  useKeyboard(
    [
      {
        key: 'k',
        modifiers: ['ctrl'],
        handler: () => handlers.onSearch?.(),
        enabled: enabled && !!handlers.onSearch,
      },
      {
        key: 'n',
        modifiers: ['ctrl'],
        handler: () => handlers.onNew?.(),
        enabled: enabled && !!handlers.onNew,
      },
      {
        key: 's',
        modifiers: ['ctrl'],
        handler: () => handlers.onSave?.(),
        enabled: enabled && !!handlers.onSave,
      },
      {
        key: 'w',
        modifiers: ['ctrl'],
        handler: () => handlers.onClose?.(),
        enabled: enabled && !!handlers.onClose,
      },
      {
        key: '?',
        modifiers: ['shift'],
        handler: () => handlers.onHelp?.(),
        enabled: enabled && !!handlers.onHelp,
      },
    ],
    [handlers, enabled]
  );
};

/**
 * Hook to detect if user is typing in an input field
 * @returns boolean indicating if user is currently typing
 */
export const useIsTyping = (): boolean => {
  const [isTyping, setIsTyping] = React.useState(false);

  useEffect(() => {
    const handleFocus = (e: FocusEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        setIsTyping(true);
      }
    };

    const handleBlur = () => {
      setIsTyping(false);
    };

    document.addEventListener('focusin', handleFocus);
    document.addEventListener('focusout', handleBlur);

    return () => {
      document.removeEventListener('focusin', handleFocus);
      document.removeEventListener('focusout', handleBlur);
    };
  }, []);

  return isTyping;
};

/**
 * Hook to trap focus within an element (for modals, dialogs)
 * @param enabled - Whether focus trap is active
 * @returns Ref to attach to the container element
 */
export const useFocusTrap = <T extends HTMLElement>(enabled: boolean = true) => {
  const containerRef = useRef<T>(null);
  const previouslyFocusedElement = useRef<Element | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const container = containerRef.current;
    if (!container) return;

    // Store previously focused element
    previouslyFocusedElement.current = document.activeElement;

    // Find all focusable elements
    const focusableElements = container.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Focus first element
    firstElement?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    container.addEventListener('keydown', handleKeyDown);

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
      // Restore focus
      (previouslyFocusedElement.current as HTMLElement)?.focus();
    };
  }, [enabled]);

  return containerRef;
};

export default useKeyboard;
