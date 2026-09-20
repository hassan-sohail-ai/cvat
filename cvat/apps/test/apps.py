# Copyright (C) 2026
# SPDX-License-Identifier: MIT

from django.apps import AppConfig


class TestConfig(AppConfig):
    name = "cvat.apps.test"
    label = "test_analytics"  # explicit label: "test" collides with Django internals
    verbose_name = "Class Distribution Analytics"
