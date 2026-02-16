import React, { useState, useEffect, useCallback } from 'react';
import { Cloud, CloudOff, Loader2 } from 'lucide-react';
import { useDriveAPI } from '@/hooks/useDriveAPI';
import { cn } from '@/lib/utils';

interface GoogleDriveConnectButtonProps {
  className?: string;
  variant?: 'button' | 'menu-item';
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export const GoogleDriveConnectButton: React.FC<GoogleDriveConnectButtonProps> = ({
  className,
  variant = 'button',
  onConnect,
  onDisconnect,
}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { checkAuth, getAuthUrl, revokeAuth } = useDriveAPI();

  // Check auth status on mount
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const status = await checkAuth();
        setIsConnected(status.authenticated);
      } catch {
        setIsConnected(false);
      }
    };
    checkConnection();
  }, [checkAuth]);

  const handleConnect = useCallback(async () => {
    setIsLoading(true);
    try {
      const { auth_url } = await getAuthUrl();
      
      // Open OAuth popup
      const width = 500;
      const height = 600;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;
      
      const popup = window.open(
        auth_url,
        'Google Drive Auth',
        `width=${width},height=${height},left=${left},top=${top}`
      );

      // Poll for popup close
      const pollTimer = setInterval(() => {
        if (popup?.closed) {
          clearInterval(pollTimer);
          // Recheck auth status
          checkAuth().then(status => {
            setIsConnected(status.authenticated);
            if (status.authenticated) {
              onConnect?.();
            }
          });
        }
      }, 500);
    } catch (error) {
      console.error('Failed to connect:', error);
    } finally {
      setIsLoading(false);
    }
  }, [getAuthUrl, checkAuth, onConnect]);

  const handleDisconnect = useCallback(async () => {
    setIsLoading(true);
    try {
      await revokeAuth();
      setIsConnected(false);
      onDisconnect?.();
    } catch (error) {
      console.error('Failed to disconnect:', error);
    } finally {
      setIsLoading(false);
    }
  }, [revokeAuth, onDisconnect]);

  const buttonContent = (
    <>
      {isLoading ? (
        <Loader2 size={18} className="animate-spin" />
      ) : isConnected ? (
        <Cloud size={18} className="text-green-500" />
      ) : (
        <CloudOff size={18} />
      )}
      <span className={variant === 'menu-item' ? 'ml-3' : 'ml-2'}>
        {isLoading ? 'Connecting...' : isConnected ? 'Drive Connected' : 'Connect Drive'}
      </span>
    </>
  );

  if (variant === 'menu-item') {
    return (
      <button
        onClick={isConnected ? handleDisconnect : handleConnect}
        disabled={isLoading}
        className={cn(
          'flex items-center w-full px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
          isConnected
            ? 'text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20'
            : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800',
          className
        )}
      >
        {buttonContent}
      </button>
    );
  }

  return (
    <button
      onClick={isConnected ? handleDisconnect : handleConnect}
      disabled={isLoading}
      className={cn(
        'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors border',
        isConnected
          ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border-green-300 dark:border-green-700 hover:bg-green-100'
          : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700',
        className
      )}
    >
      {buttonContent}
    </button>
  );
};

export default GoogleDriveConnectButton;
