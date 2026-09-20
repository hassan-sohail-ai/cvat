# CVAT Advanced Analytics & Real-Time WebSocket Integration (Level 3)

This repository contains the enterprise-grade implementation of real-time class distribution analytics, asynchronous background monitoring, and live WebSocket synchronization for **CVAT (Computer Vision Annotation Tool)**.

---

## 🏗️ 1. System Architecture & Component Breakdown

The solution extends the existing containerized stack without introducing external bottlenecks, adhering to a clean separation of concerns:

```
[ Frontend: React / AntD / Recharts ] 
         │ (HTTP REST / WebSocket /ws/)
         ▼
[ Traefik Reverse Proxy (Port 8080) ]
         │
         ├──► /api/v1/tasks/{id}/analytics (Django REST Framework)
         └──► /ws/tasks/{id}/ (Custom ASGI WebSocket / Uvicorn)
                     │
                     ▼
           [ PostgreSQL & Redis Broker ]
```

* **Traefik Reverse Proxy:** Manages public entry points, routing API requests, static assets, and WebSocket streams securely to the backend workers.
* **Django ASGI Backend & Uvicorn:** Handles concurrent connection pools and low-latency event broadcasts.
* **PostgreSQL Database:** Executes optimized aggregation queries utilizing Django ORM (`values()`, `annotate()`) to calculate real-time class frequencies with zero per-row query overhead.

---

## 🔌 2. API & WebSocket Specification

### REST Analytics Endpoint
* **Route:** `/api/v1/tasks/{id}/analytics`
* **Method:** `GET`
* **Authentication:** Session cookie / Basic Auth (Admin or assigned user)
* **Response Payload (JSON):**
  ```json
  {
    "task_id": 1,
    "total_images": 120,
    "total_annotations": 450,
    "class_distribution": {
      "car": 300,
      "pedestrian": 150
    }
  }
  ```

### Real-Time WebSocket Stream
* **Route:** `/ws/tasks/{task_id}/`
* **Protocol:** `wss://` (production) / `ws://` (development)
* **Behavior:** Transmits live updates when shape states or bounding boxes are modified inside the annotation interface. Includes automatic session re-authorization every 60 seconds.

---

## ⚙️ 3. Engineering Challenges & Solutions

1. **Storage Optimization & Pruning:** 
   * *Issue:* Heavy Docker build layers caused disk usage on development environments to exceed threshold limits.
   * *Resolution:* Implemented automated cleanup sequences via `docker system prune -a --volumes -f`.
2. **Port Collisions:**
   * *Issue:* Conflict on port `8080` between custom backend workers and the Traefik routing configuration.
   * *Resolution:* Remapped and verified service bindings inside `docker-compose.yml`.
3. **Missing Django Signals during Bulk Operations:**
   * *Issue:* `bulk_create` operations bypassed traditional save signals.
   * *Resolution:* Implemented lightweight database fingerprinting polling every 2 seconds to safely broadcast delta state changes.

---

## 🚀 4. Quick Start & Execution Guide

1. **Checkout the working branch:**
   ```bash
   git checkout dev-test01
   ```

2. **Spin up the Docker container ecosystem:**
   ```bash
   docker compose up -d
   ```

3. **Verify the backend REST endpoint:**
   ```bash
   curl -u admin:<your_password> "http://localhost:8080/api/v1/tasks/1/analytics"
   ```

4. **Access the Web Interface:**
   Open your browser and navigate to `http://localhost:8080` to view the live dashboard and real-time annotation sync.