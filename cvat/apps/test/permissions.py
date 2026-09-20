# Copyright (C) 2026
# SPDX-License-Identifier: MIT

from django.db.models import Q

from cvat.apps.engine.models import Task


def visible_tasks(user):
    if not user or not user.is_authenticated:
        return Task.objects.none()
    if user.is_superuser or user.is_staff:
        return Task.objects.all()
    return Task.objects.filter(
        Q(owner_id=user.id)
        | Q(assignee_id=user.id)
        | Q(project__owner_id=user.id)
        | Q(project__assignee_id=user.id)
        | Q(segment__job__assignee_id=user.id)
    ).distinct()


def user_can_view_task(user, task) -> bool:
    return visible_tasks(user).filter(pk=task.id if hasattr(task, "id") else task).exists()
