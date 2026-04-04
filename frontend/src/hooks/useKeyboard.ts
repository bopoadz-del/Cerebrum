import { useState, useEffect, useCallback } from 'react';

interface KeyboardState {
  isOpen: boolean;
  height: number;
  offsetTop: number;
}

interface UseKeyboardOptions {
  onOpen?: () => void;
  onClose?: () => void;
}

export function useKeyboard(options: UseKeyboardOptions = {}): KeyboardState {
  const [keyboardState, setKeyboardState] = useState<KeyboardState>({
    isOpen: false,
    height: 0,
    offsetTop: 0,
  });

  const handleResize = useCallback(() => {
    if (typeof window === 'undefined' || !window.visualViewport) return;

    const viewport = window.visualViewport;
    const windowHeight = window.innerHeight;
    const viewportHeight = viewport.height;
    const viewportOffsetTop = viewport.offsetTop;
    
    // Keyboard is likely open if viewport height is significantly smaller than window height
    // We use a threshold of 200px to account for other UI elements
    const isKeyboardOpen = windowHeight - viewportHeight > 200;
    const keyboardHeight = isKeyboardOpen ? windowHeight - viewportHeight : 0;

    setKeyboardState({
      isOpen: isKeyboardOpen,
      height: keyboardHeight,
      offsetTop: viewportOffsetTop,
    });

    if (isKeyboardOpen && !keyboardState.isOpen) {
      options.onOpen?.();
    } else if (!isKeyboardOpen && keyboardState.isOpen) {
      options.onClose?.();
    }
  }, [keyboardState.isOpen, options.onOpen, options.onClose]);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Use visualViewport API if available (modern browsers/iOS)
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', handleResize);
      window.visualViewport.addEventListener('scroll', handleResize);
      
      // Initial check
      handleResize();

      return () => {
        window.visualViewport?.removeEventListener('resize', handleResize);
        window.visualViewport?.removeEventListener('scroll', handleResize);
      };
    } else {
      // Fallback for older browsers
      const handleWindowResize = () => {
        const windowHeight = window.innerHeight;
        const isKeyboardOpen = windowHeight < (window.screen.height * 0.7);
        
        setKeyboardState(prev => ({
          ...prev,
          isOpen: isKeyboardOpen,
        }));
      };

      window.addEventListener('resize', handleWindowResize);
      return () => window.removeEventListener('resize', handleWindowResize);
    }
  }, [handleResize]);

  return keyboardState;
}

export default useKeyboard;
