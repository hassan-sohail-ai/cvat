# Copyright (C) 2026
# SPDX-License-Identifier: MIT

from django.urls import path

from .views import ClassDistributionView

urlpatterns = [
    path("class-distribution", ClassDistributionView.as_view(), name="class-distribution"),
]
