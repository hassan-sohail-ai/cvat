# Copyright (C) 2026
# SPDX-License-Identifier: MIT

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cvat.apps.engine.models import Task

from .permissions import user_can_view_task
from .serializers import ClassDistributionSerializer
from .services import compute_class_distribution


class ClassDistributionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Class-wise image and annotation counts for a task",
        parameters=[
            OpenApiParameter(
                "task_id", int, required=True, description="Target task id"
            )
        ],
        responses={200: ClassDistributionSerializer},
    )
    def get(self, request):
        raw_id = request.query_params.get("task_id")
        if not raw_id or not raw_id.isdigit():
            return Response(
                {"detail": "A numeric 'task_id' query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task = get_object_or_404(Task, pk=int(raw_id))
        if not user_can_view_task(request.user, task):
            return Response(
                {"detail": "You do not have permission to view this task."},
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = compute_class_distribution(task.id)
        return Response(ClassDistributionSerializer(payload).data)
