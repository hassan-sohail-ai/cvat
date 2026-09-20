// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import React, { useEffect, useState } from 'react';
import { Card } from 'antd/lib/card';
import Spin from 'antd/lib/spin';
import notification from 'antd/lib/notification';
import Tag from 'antd/lib/tag';

interface ClassDistributionWidgetProps {
    taskId: number;
}

export function ClassDistributionWidget({ taskId }: ClassDistributionWidgetProps): JSX.Element {
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState<any>(null);
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const wsUrl = `${protocol}${window.location.host}/ws/analytics/tasks/${taskId}/class-distribution/`;

        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('✅ WebSocket Connected Successfully!');
            setIsConnected(true);
            setLoading(false);
        };

        ws.onmessage = (event) => {
            try {
                const response = JSON.parse(event.data);
                console.log('📦 Received Data:', response);
                if (response.type === 'snapshot' || response.type === 'update') {
                    setStats(response.data);
                }
            } catch (err) {
                console.error('Error parsing WS data:', err);
            }
        };

        ws.onerror = (error) => {
            console.error('❌ WebSocket Error:', error);
            notification.error({
                message: 'WebSocket Connection Error',
                description: 'Could not establish real-time connection for class distribution.',
            });
            setLoading(false);
        };

        ws.onclose = () => {
            console.log('🔌 WebSocket Disconnected');
            setIsConnected(false);
        };

        return () => {
            ws.close();
        };
    }, [taskId]);

    return (
        <Card
            className='cvat-class-distribution-widget'
            title={
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Class Distribution (Task #{taskId})</span>
                    <Tag color={isConnected ? 'green' : 'red'}>
                        {isConnected ? 'Live Connected' : 'Disconnected'}
                    </Tag>
                </div>
            }
            style={{ marginTop: 20 }}
        >
            {loading ? (
                <div style={{ textAlign: 'center', padding: '20px' }}>
                    <Spin />
                </div>
            ) : (
                <div>
                    {stats ? (
                        <div>
                            <p style={{ fontWeight: '500', marginBottom: '12px' }}>
                                Total Annotations: {stats.total_annotations || 0}
                            </p>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                                {stats.classes?.map((cls: any, idx: number) => (
                                    <div
                                        key={idx}
                                        style={{
                                            borderLeft: `4px solid ${cls.color || '#1890ff'}`,
                                            background: '#f5f5f5',
                                            padding: '10px',
                                            borderRadius: '4px',
                                            minWidth: '140px',
                                            flex: 1
                                        }}
                                    >
                                        <div style={{ fontWeight: 'bold' }}>{cls.name}</div>
                                        <div style={{ fontSize: '12px', color: '#555' }}>Count: {cls.annotation_count}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <p style={{ color: '#888', textAlign: 'center' }}>Waiting for real-time statistics...</p>
                    )}
                </div>
            )}
        </Card>
    );
}