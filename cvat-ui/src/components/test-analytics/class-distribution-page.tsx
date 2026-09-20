// Copyright (C) 2026
// SPDX-License-Identifier: MIT

import React from 'react';
import { useParams } from 'react-router-dom';
import {
    Alert, Button, Card, Col, Empty, Row, Space, Spin, Statistic, Table, Tag, Typography,
} from 'antd';
import {
    Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

import useClassDistribution, { ClassCount, SocketStatus } from './use-class-distribution';

const STATUS_COLOR: Record<SocketStatus, string> = {
    connecting: 'blue',
    live: 'green',
    reconnecting: 'orange',
    offline: 'red',
};

const STATUS_LABEL: Record<SocketStatus, string> = {
    connecting: 'Connecting',
    live: 'Live',
    reconnecting: 'Reconnecting',
    offline: 'Offline, retrying',
};

const columns = [
    {
        title: 'Class',
        dataIndex: 'name',
        key: 'name',
        render: (name: string, row: ClassCount) => (
            <Space>
                <span
                    style={{
                        display: 'inline-block',
                        width: 10,
                        height: 10,
                        borderRadius: 2,
                        background: row.color,
                    }}
                />
                {name}
            </Space>
        ),
    },
    { title: 'Images', dataIndex: 'image_count', key: 'image_count' },
    { title: 'Annotations', dataIndex: 'annotation_count', key: 'annotation_count' },
];

function Dashboard({ taskId }: { taskId: number }): JSX.Element {
    const {
        data, status, error, refresh,
    } = useClassDistribution(taskId);

    return (
        <div className='cvat-class-distribution-page' style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }}>
            <Space
                align='center'
                wrap
                style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}
            >
                <Typography.Title level={3} style={{ margin: 0 }}>
                    {data ? `Class distribution: ${data.task_name}` : 'Class distribution'}
                </Typography.Title>
                <Space>
                    <Tag color={STATUS_COLOR[status]}>{STATUS_LABEL[status]}</Tag>
                    <Button onClick={refresh}>Refresh</Button>
                </Space>
            </Space>

            {error && (
                <Alert
                    showIcon
                    type={data ? 'warning' : 'error'}
                    message={error}
                    style={{ marginBottom: 16 }}
                />
            )}

            {!data && !error && (
                <div style={{ textAlign: 'center', padding: 64 }}>
                    <Spin size='large' />
                </div>
            )}

            {data && (
                <>
                    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                        <Col xs={24} sm={8}>
                            <Card><Statistic title='Frames' value={data.total_frames} /></Card>
                        </Col>
                        <Col xs={24} sm={8}>
                            <Card><Statistic title='Frames with annotations' value={data.annotated_frames} /></Card>
                        </Col>
                        <Col xs={24} sm={8}>
                            <Card><Statistic title='Annotations' value={data.total_annotations} /></Card>
                        </Col>
                    </Row>

                    <Card title='Images per class' style={{ marginBottom: 16 }}>
                        {data.classes.length === 0 ? (
                            <Empty description='This task has no annotations yet' />
                        ) : (
                            <ResponsiveContainer width='100%' height={320}>
                                <BarChart data={data.classes} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                                    <CartesianGrid strokeDasharray='3 3' stroke='rgba(128,128,128,0.25)' />
                                    <XAxis dataKey='name' />
                                    <YAxis allowDecimals={false} />
                                    <Tooltip />
                                    {/* Animation off: live updates should not make bars jitter. */}
                                    <Bar dataKey='image_count' name='Images' isAnimationActive={false}>
                                        {data.classes.map((item) => (
                                            <Cell key={item.label_id} fill={item.color} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </Card>

                    <Card title='Details'>
                        <Table
                            size='small'
                            rowKey='label_id'
                            pagination={false}
                            columns={columns}
                            dataSource={data.classes}
                        />
                    </Card>
                </>
            )}
        </div>
    );
}

export default function ClassDistributionPage(): JSX.Element {
    const { id } = useParams<{ id: string }>();
    const taskId = Number(id);

    if (!Number.isInteger(taskId) || taskId <= 0) {
        return <Alert showIcon type='error' message='Invalid task id in the address' style={{ margin: 24 }} />;
    }
    return <Dashboard taskId={taskId} />;
}