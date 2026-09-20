# Copyright (C) 2026
# SPDX-License-Identifier: MIT

from rest_framework import serializers


class ClassCountSerializer(serializers.Serializer):
    label_id = serializers.IntegerField()
    name = serializers.CharField()
    color = serializers.CharField()
    image_count = serializers.IntegerField()
    annotation_count = serializers.IntegerField()


class ClassDistributionSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    task_name = serializers.CharField()
    total_frames = serializers.IntegerField()
    annotated_frames = serializers.IntegerField()
    total_annotations = serializers.IntegerField()
    classes = ClassCountSerializer(many=True)
