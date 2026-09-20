# Copyright (C) 2026
# SPDX-License-Identifier: MIT
"""
Aggregation layer: turns CVAT's normalised annotation tables into a
class-wise (label-wise) distribution for a single task.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.db.models import Count, Q

from cvat.apps.engine.models import (
    Label,
    LabeledImage,
    LabeledShape,
    Task,
    TrackedShape,
)


def _labels_of_task(task: Task):
    condition = Q(task_id=task.id)
    if task.project_id is not None:
        condition |= Q(project_id=task.project_id)
    return Label.objects.filter(condition).order_by("id")


def _frame_pairs(task_id: int):
    yield from LabeledShape.objects.filter(
        job__segment__task_id=task_id
    ).values_list("label_id", "frame")

    yield from LabeledImage.objects.filter(
        job__segment__task_id=task_id
    ).values_list("label_id", "frame")

    yield from TrackedShape.objects.filter(
        track__job__segment__task_id=task_id, outside=False
    ).values_list("track__label_id", "frame")


def _annotation_totals(task_id: int) -> dict[int, int]:
    totals: dict[int, int] = defaultdict(int)

    for row in (
        LabeledShape.objects.filter(job__segment__task_id=task_id)
        .values("label_id")
        .annotate(n=Count("id"))
    ):
        totals[row["label_id"]] += row["n"]

    for row in (
        LabeledImage.objects.filter(job__segment__task_id=task_id)
        .values("label_id")
        .annotate(n=Count("id"))
    ):
        totals[row["label_id"]] += row["n"]

    for row in (
        TrackedShape.objects.filter(
            track__job__segment__task_id=task_id, outside=False
        )
        .values("track__label_id")
        .annotate(n=Count("id"))
    ):
        totals[row["track__label_id"]] += row["n"]

    return totals


def compute_class_distribution(task_id: int) -> dict[str, Any]:
    task = Task.objects.select_related("data", "project").get(pk=task_id)

    frames_by_label: dict[int, set[int]] = defaultdict(set)
    for label_id, frame in _frame_pairs(task_id):
        frames_by_label[label_id].add(frame)

    totals = _annotation_totals(task_id)

    classes = []
    annotated_frames: set[int] = set()
    for label in _labels_of_task(task):
        frames = frames_by_label.get(label.id, set())
        annotated_frames |= frames
        classes.append(
            {
                "label_id": label.id,
                "name": label.name,
                "color": label.color,
                "image_count": len(frames),
                "annotation_count": totals.get(label.id, 0),
            }
        )

    classes.sort(key=lambda row: (-row["image_count"], row["name"]))

    total_frames = task.data.size if task.data_id else 0
    return {
        "task_id": task.id,
        "task_name": task.name,
        "total_frames": total_frames,
        "annotated_frames": len(annotated_frames),
        "total_annotations": sum(totals.values()),
        "classes": classes,
    }
