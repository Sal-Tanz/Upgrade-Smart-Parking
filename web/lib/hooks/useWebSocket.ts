'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface UseWebSocketOptions {
  url: string;
  onMessage?: (data: any) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export interface UseWebSocketReturn {
  connectionStatus: ConnectionStatus;
  lastMessage: any;
  sendMessage: (data: any) => void;
  disconnect: () => void;
  reconnect: () => void;
}

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const {
    url,
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnect: autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options;

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<any>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnectRef = useRef(autoReconnect);

  const onMessageRef = useRef(onMessage);
  const onOpenRef = useRef(onOpen);
  const onCloseRef = useRef(onClose);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onMessageRef.current = onMessage;
    onOpenRef.current = onOpen;
    onCloseRef.current = onClose;
    onErrorRef.current = onError;
    shouldReconnectRef.current = autoReconnect;
  }, [onMessage, onOpen, onClose, onError, autoReconnect]);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    const ws = wsRef.current;
    wsRef.current = null;

    if (ws) {
      ws.close();
    }

    setConnectionStatus('disconnected');
  }, []);

  const connect = useCallback(() => {
    shouldReconnectRef.current = autoReconnect;

    try {
      setConnectionStatus('connecting');
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (wsRef.current !== ws) return;
        console.log('[WebSocket] Connected');
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;
        onOpenRef.current?.();
      };

      ws.onmessage = (event) => {
        if (wsRef.current !== ws) return;

        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          onMessageRef.current?.(data);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      ws.onclose = () => {
        if (wsRef.current !== ws) return;
        wsRef.current = null;
        console.log('[WebSocket] Disconnected');
        setConnectionStatus('disconnected');
        onCloseRef.current?.();

        if (shouldReconnectRef.current && reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          console.log(`[WebSocket] Reconnecting... Attempt ${reconnectAttempts.current}/${maxReconnectAttempts}`);

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null;
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = (error) => {
        if (wsRef.current !== ws) return;
        console.error('[WebSocket] Error:', error);
        setConnectionStatus('error');
        onErrorRef.current?.(error);
      };
    } catch (error) {
      console.error('[WebSocket] Failed to connect:', error);
      setConnectionStatus('error');
    }
  }, [url, autoReconnect, reconnectInterval, maxReconnectAttempts]);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttempts.current = 0;
    shouldReconnectRef.current = autoReconnect;
    connect();
  }, [autoReconnect, connect, disconnect]);

  const sendMessage = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('[WebSocket] Cannot send message: not connected');
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    connectionStatus,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect,
  };
}
