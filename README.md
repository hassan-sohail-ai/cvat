# CVAT Real-Time Class Distribution Analytics & WebSocket Integration

This repository contains the complete full-stack extension of **CVAT (Computer Vision Annotation Tool)**, featuring real-time class-wise analytics, interactive data visualization, and live WebSocket synchronization.

---

## 🚀 Key Features Implemented

* **Class-Wise Analytics REST API:** Computes image/frame counts, total annotations, and class distributions with high performance using database-level aggregation (`values()` & `annotate()`) with zero per-row queries.
* **Custom ASGI WebSocket Wrapper:** Integrated a lightweight ASGI middleware (`cvat/asgi.py` & `realtime.py`) to stream real-time updates over `/ws/analytics/tasks/<id>/class-distribution/` without adding heavy dependencies like Django Channels or triggering lengthy image rebuilds.
* **Secure Handshake & Token/Session Auth:** Enforces robust security including session-cookie resolution, `permissions.user_can_view_task` checks, origin validation, and automatic periodic re-authorization (every 60s) with custom close codes (`4401` / `4403`).
* **Efficient Change Detection (Fingerprinting):** Bypasses missing Django signals during `bulk_create` operations by running a lightweight database fingerprint query every 2 seconds (checking row counts, newest IDs, and job modification dates) to broadcast updates only when changes occur.
* **Resilient Frontend Hook & UI (`useClassDistribution`):** Built with Ant Design and Recharts, featuring fast first-paint via parallel REST fetch, exponential backoff reconnection with jitter, update throttling, and live connection status badges (`connecting`, `live`, `reconnecting`, `offline`).

---

## 🛠️ Architecture & Data Flow

1. **Traefik Proxy (Port 8080):** Acts as the single public entry point, routing `/api/`, `/static/`, `/admin/`, and the added `/ws/` paths directly to the backend ASGI server (`uvicorn`), while serving the UI frontend.
2. **Database Aggregation:** Calculates distinct frame counts per class and annotation metrics directly inside PostgreSQL.
3. **Data Sync Flow:**
   * **Initial Load:** Opens page `/tasks/:id/class-distribution`, fetching a quick initial snapshot over REST.
   * **Live Stream:** Establishes a WebSocket connection. When users modify or save bounding boxes, the backend detects fingerprint shifts and broadcasts the updated distribution JSON payload.

---

## ⚙️ Quick Start & Setup

1. **Spin up the Docker containers** (Traefik running on port `8080`):
   ```bash
   docker compose up -d
   ```

2. **Run the frontend development server** with API proxy configuration:
   ```bash
   yarn run start:cvat-ui --env API_URL=http://localhost:8080
   ```

3. **Verify the REST endpoint** via terminal:
   ```bash
   curl -u admin:<your_password> "http://localhost:8080/api/test/class-distribution?task_id=1"
   ```

4. **Live Verification:** Open `/tasks/1/class-distribution` in your browser, wait for the **Live** badge, and draw/save a shape inside the annotation workspace—the charts and counters update automatically within ~2 seconds!