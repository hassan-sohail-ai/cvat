// Copyright (C) 2026
// SPDX-License-Identifier: MIT

import {
    useCallback, useEffect, useRef, useState,
} from 'react';

export interface ClassCount {
    label_id: number;
    name: string;
    color: string;
    image_count: number;
    annotation_count: number;
}

export interface Distribution {
    task_id: number;
    task_name: string;
    total_frames: number;
    annotated_frames: number;
    total_annotations: number;
    classes: ClassCount[];
}

export type SocketStatus = 'connecting' | 'live' | 'reconnecting' | 'offline';

const BASE_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 30000;
// After this many failed attempts the badge shows "offline", but retries continue.
const ATTEMPTS_BEFORE_OFFLINE = 5;
// Minimum gap between two UI re-renders caused by socket messages.
const THROTTLE_MS = 300;

function socketURL(taskId: number): string {
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${scheme}://${window.location.host}/ws/analytics/tasks/${taskId}/class-distribution/`;
}

export default function useClassDistribution(taskId: number): {
    data: Distribution | null;
    status: SocketStatus;
    error: string | null;
    refresh: () => void;
} {
    const [data, setData] = useState<Distribution | null>(null);
    const [status, setStatus] = useState<SocketStatus>('connecting');
    const [error, setError] = useState<string | null>(null);

    // Shared with refresh(); everything else lives inside the effect so that
    // each taskId gets its own private socket, timers and "disposed" flag.
    const socketRef = useRef<WebSocket | null>(null);
    const snapshotRef = useRef<() => Promise<void>>(async () => {});

    useEffect(() => {
        let disposed = false;
        let attempt = 0;
        let socket: WebSocket | null = null;
        let retryTimer: number | null = null;
        let cooldownTimer: number | null = null;
        let pending: Distribution | null = null;

        setData(null);
        setError(null);
        setStatus('connecting');

        // Leading + trailing throttle: the first update renders immediately,
        // updates arriving during the cool-down are collapsed into the latest one.
        const applySnapshot = (next: Distribution): void => {
            if (cooldownTimer !== null) {
                pending = next;
                return;
            }
            setData(next);
            setError(null);
            cooldownTimer = window.setTimeout(() => {
                cooldownTimer = null;
                if (pending && !disposed) {
                    const queued = pending;
                    pending = null;
                    applySnapshot(queued);
                }
            }, THROTTLE_MS);
        };

        const fetchSnapshot = async (): Promise<void> => {
            try {
                const response = await fetch(`/api/test/class-distribution?task_id=${taskId}`, {
                    credentials: 'same-origin',
                });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const payload = (await response.json()) as Distribution;
                if (!disposed) applySnapshot(payload);
            } catch (err) {
                if (!disposed) setError((err as Error).message);
            }
        };
        snapshotRef.current = fetchSnapshot;

        function connect(): void {
            if (disposed) return;
            retryTimer = null;

            const retry = (): void => {
                if (disposed) return;
                attempt += 1;
                setStatus(attempt > ATTEMPTS_BEFORE_OFFLINE ? 'offline' : 'reconnecting');
                // Exponential backoff with "equal jitter": never zero, never a thundering herd.
                const ceiling = Math.min(BASE_BACKOFF_MS * 2 ** (attempt - 1), MAX_BACKOFF_MS);
                const delay = ceiling / 2 + Math.random() * (ceiling / 2);
                // Keep the chart fresh over plain HTTP while the socket is down.
                fetchSnapshot();
                retryTimer = window.setTimeout(connect, delay);
            };

            let current: WebSocket;
            try {
                current = new WebSocket(socketURL(taskId));
            } catch {
                retry();
                return;
            }
            socket = current;
            socketRef.current = current;

            current.onopen = () => {
                attempt = 0;
                setStatus('live');
                setError(null);
            };

            current.onmessage = (event: MessageEvent) => {
                let message: { type?: string; data?: Distribution; detail?: string };
                try {
                    message = JSON.parse(event.data);
                } catch {
                    return; // ignore malformed frames instead of crashing the handler
                }
                if (message.type === 'snapshot' && message.data) {
                    applySnapshot(message.data);
                } else if (message.type === 'error') {
                    setError(message.detail ?? 'Server error');
                }
            };

            current.onclose = (event: CloseEvent) => {
                // A newer socket (or unmount) already took over: ignore this one.
                if (socket !== current) return;
                socket = null;
                socketRef.current = null;
                if (disposed) return;

                if (event.code === 4401 || event.code === 4403) {
                    // Auth problems will not fix themselves: stop retrying.
                    setStatus('offline');
                    setError(event.code === 4401 ?
                        'Session expired. Please sign in again.' :
                        'You do not have access to this task.');
                    return;
                }
                retry();
            };
        }

        // Come back immediately when the browser regains network.
        const onOnline = (): void => {
            if (disposed || (socket && socket.readyState !== WebSocket.CLOSED)) return;
            if (retryTimer !== null) window.clearTimeout(retryTimer);
            attempt = 0;
            connect();
        };
        window.addEventListener('online', onOnline);

        fetchSnapshot(); // first paint does not wait for the socket
        connect();

        return () => {
            disposed = true;
            window.removeEventListener('online', onOnline);
            if (retryTimer !== null) window.clearTimeout(retryTimer);
            if (cooldownTimer !== null) window.clearTimeout(cooldownTimer);
            if (socket) {
                socket.onclose = null;
                socket.close(1000, 'unmount');
            }
            socket = null;
            socketRef.current = null;
        };
    }, [taskId]);

    const refresh = useCallback(() => {
        const socket = socketRef.current;
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: 'refresh' }));
        } else {
            snapshotRef.current();
        }
    }, []);

    return {
        data, status, error, refresh,
    };
}