# Vultr Deployment Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          VULTR SERVER                               │
│                    (2 vCPU, 4GB RAM, $18/mo)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                     NGINX (Port 80/443)                       │ │
│  │              - SSL Termination                                │ │
│  │              - Reverse Proxy                                  │ │
│  │              - Rate Limiting                                  │ │
│  └────────────────────┬──────────────────────────────────────────┘ │
│                       │                                             │
│  ┌────────────────────┴──────────────────────────────────────────┐ │
│  │            APPLICATION LAYER (Docker Containers)              │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │                                                               │ │
│  │  ┌──────────────────────┐      ┌──────────────────────┐      │ │
│  │  │   FastAPI Backend    │──────│  PostgreSQL 16       │      │ │
│  │  │   (Port 8000)        │      │  (Port 5432)         │      │ │
│  │  │                      │      │                      │      │ │
│  │  │  - JWT Auth          │      │  - User data         │      │ │
│  │  │  - REST API          │      │  - Posts             │      │ │
│  │  │  - Rate Limiting     │      │  - Connections       │      │ │
│  │  │  - /metrics endpoint │      │                      │      │ │
│  │  └──────────────────────┘      └──────────────────────┘      │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │         OBSERVABILITY LAYER (Docker Containers)               │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │                                                               │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │ │
│  │  │  Prometheus  │  │     Loki     │  │   Grafana    │       │ │
│  │  │  (Port 9090) │  │ (Port 3100)  │  │ (Port 3000)  │       │ │
│  │  │              │  │              │  │              │       │ │
│  │  │  - Metrics   │  │  - Logs      │  │  - Dashboards│       │ │
│  │  │  - Alerts    │  │  - Search    │  │  - Viz       │       │ │
│  │  └──────┬───────┘  └──────▲───────┘  └──────────────┘       │ │
│  │         │                  │                                 │ │
│  │         │          ┌───────┴────────┐                        │ │
│  │         │          │   Promtail     │                        │ │
│  │         │          │  (Port 9080)   │                        │ │
│  │         │          │                │                        │ │
│  │         │          │  - Log Collect │                        │ │
│  │         │          └────────────────┘                        │ │
│  │         │                                                     │ │
│  │  ┌──────┴──────────────────────────┐                         │ │
│  │  │      Alertmanager               │                         │ │
│  │  │      (Port 9093)                │                         │ │
│  │  │                                 │                         │ │
│  │  │  - Email alerts                 │                         │ │
│  │  │  - Alert routing                │                         │ │
│  │  └─────────────────────────────────┘                         │ │
│  │                                                               │ │
│  │  ┌──────────────┐  ┌──────────────┐                         │ │
│  │  │ Node Exporter│  │Postgres Expo.│                         │ │
│  │  │ (Port 9100)  │  │ (Port 9187)  │                         │ │
│  │  │              │  │              │                         │ │
│  │  │ - System     │  │ - DB metrics │                         │ │
│  │  │   metrics    │  │              │                         │ │
│  │  └──────────────┘  └──────────────┘                         │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    STORAGE LAYER                              │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │                                                               │ │
│  │  - postgres_data (Database)                                  │ │
│  │  - backend_logs (Application logs)                           │ │
│  │  - grafana_data (Dashboards & config)                        │ │
│  │  - prometheus_data (Metrics storage)                         │ │
│  │  - loki_data (Log storage)                                   │ │
│  │  - /home/deploy/backups (Daily DB backups)                   │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

                              ▲  │
                              │  │
                              │  ▼
                    ┌─────────────────────┐
                    │     INTERNET        │
                    │                     │
                    │  - API Clients      │
                    │  - Developers       │
                    │  - Monitoring       │
                    └─────────────────────┘
```

## Data Flow Diagrams

### 1. API Request Flow
```
User/Client
    │
    ▼
[Internet] → [Firewall (UFW)]
    │            Ports: 80, 443
    ▼
[Nginx Proxy]
    │
    ├─ Rate Limiting
    ├─ SSL Termination
    └─ Request Logging
    │
    ▼
[FastAPI Backend]
    │
    ├─ JWT Validation
    ├─ Request Processing
    ├─ Security Headers
    └─ Business Logic
    │
    ▼
[PostgreSQL Database]
    │
    └─ Query Execution
    │
    ▼
[Response] → Client
```

### 2. Metrics Collection Flow
```
[FastAPI Backend]
    │
    ├─ /metrics endpoint (Prometheus format)
    │   └─ Request count, duration, errors
    │
    ▼
[Prometheus] ←─ Scrape every 15s
    │
    ├─ Store time-series data
    ├─ Evaluate alert rules
    ├─ Query by Grafana
    │
    ▼
[Alert Rules Triggered?]
    │
    ├─ Yes → [Alertmanager] → Email
    │
    └─ No → Continue monitoring

[PostgreSQL]
    │
    ▼
[Postgres Exporter] ←─ Query DB metrics
    │
    ├─ Connection pool
    ├─ Query performance
    └─ Database size
    │
    ▼
[Prometheus] ←─ Scrape every 15s

[System]
    │
    ▼
[Node Exporter] ←─ Collect system stats
    │
    ├─ CPU, Memory
    ├─ Disk I/O
    └─ Network
    │
    ▼
[Prometheus] ←─ Scrape every 15s
```

### 3. Logging Flow
```
[Docker Containers]
    │
    ├─ Backend logs (stdout/stderr)
    ├─ Database logs
    ├─ Nginx logs
    │
    ▼
[Promtail] ←─ Tail logs
    │
    ├─ Parse log format
    ├─ Add labels (container, service)
    └─ Forward to Loki
    │
    ▼
[Loki]
    │
    ├─ Index labels
    ├─ Store log data
    └─ Enable search
    │
    ▼
[Grafana] ←─ Query logs
    │
    └─ Display in dashboards
```

### 4. Alerting Flow
```
[Prometheus]
    │
    ├─ Evaluate rules every 30s
    │
    ▼
[Alert Rule: High Error Rate]
    │
    ├─ Check: error_rate > 5% for 2 minutes
    │
    ▼
[Condition Met?]
    │
    ├─ No → Continue monitoring
    │
    └─ Yes ▼
           [Fire Alert]
               │
               ▼
           [Alertmanager]
               │
               ├─ Group similar alerts
               ├─ Apply routing rules
               ├─ Check inhibition rules
               │
               ▼
           [Send Notification]
               │
               ├─ Email (SMTP)
               ├─ Slack (webhook) - optional
               └─ PagerDuty (API) - optional
```

### 5. Backup Flow
```
[Cron Job] (Daily at 2 AM)
    │
    ▼
[backup.sh script]
    │
    ├─ pg_dump from container
    │
    ▼
[SQL Dump File]
    │
    ├─ backup_YYYYMMDD_HHMMSS.sql
    │
    ▼
[Compress with gzip]
    │
    ├─ backup_YYYYMMDD_HHMMSS.sql.gz
    │
    ▼
[Store in /home/deploy/backups]
    │
    ├─ Keep last 7 days
    │
    ▼
[Optional: Upload to S3/B2]
    │
    └─ Off-site backup
```

## Port Mapping

### External (Public)
- **80** → Nginx (HTTP) → Redirects to HTTPS
- **443** → Nginx (HTTPS) → Backend
- **3000** → Grafana UI (Internal access only, expose via SSH tunnel)
- **22** → SSH (For admin access)

### Internal (Docker Network)
- **8000** → FastAPI Backend
- **5432** → PostgreSQL Database
- **9090** → Prometheus
- **3100** → Loki
- **9080** → Promtail
- **9093** → Alertmanager
- **9100** → Node Exporter
- **9187** → Postgres Exporter

## Network Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Public Network                         │
│                   (Internet-facing)                         │
│                                                             │
│     Port 80/443 (HTTPS)    Port 22 (SSH)                   │
│            │                      │                         │
└────────────┼──────────────────────┼─────────────────────────┘
             │                      │
             ▼                      ▼
        ┌────────────┐        ┌────────────┐
        │   Nginx    │        │    SSH     │
        └─────┬──────┘        └────────────┘
              │
              │
┌─────────────┼───────────────────────────────────────────────┐
│             │        Docker Bridge Network                  │
│             │        (Internal communication)               │
│             │                                               │
│             ▼                                               │
│      ┌──────────────┐                                       │
│      │   Backend    │ ──────┬───────┐                      │
│      │   :8000      │       │       │                      │
│      └──────────────┘       │       │                      │
│             │               │       │                      │
│             │               ▼       ▼                      │
│             │         ┌──────────┐ ┌──────────────┐        │
│             └────────→│PostgreSQL│ │  Prometheus  │        │
│                       │  :5432   │ │    :9090     │        │
│                       └──────────┘ └──────┬───────┘        │
│                             │             │                │
│                             │             │                │
│                             ▼             ▼                │
│                       ┌──────────┐  ┌──────────┐           │
│                       │  Postgres│  │   Loki   │           │
│                       │ Exporter │  │  :3100   │           │
│                       │  :9187   │  └────▲─────┘           │
│                       └──────────┘       │                 │
│                                          │                 │
│                       ┌──────────┐  ┌────┴─────┐           │
│                       │   Node   │  │Promtail  │           │
│                       │ Exporter │  │  :9080   │           │
│                       │  :9100   │  └──────────┘           │
│                       └──────────┘                         │
│                                                            │
│                       ┌──────────────┐                     │
│                       │   Grafana    │                     │
│                       │    :3000     │                     │
│                       └──────────────┘                     │
│                       ┌──────────────┐                     │
│                       │ Alertmanager │                     │
│                       │    :9093     │                     │
│                       └──────────────┘                     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Application Layer
- **Nginx**: Entry point, SSL, rate limiting, load balancing
- **FastAPI**: Business logic, API endpoints, authentication
- **PostgreSQL**: Data persistence, relational data

### Observability Layer
- **Prometheus**: Metrics collection, storage, alerting
- **Loki**: Log aggregation and storage
- **Promtail**: Log collection from containers
- **Grafana**: Visualization and dashboards
- **Alertmanager**: Alert routing and notifications
- **Node Exporter**: System-level metrics
- **Postgres Exporter**: Database-specific metrics

### Security Layer
- **UFW Firewall**: Network-level access control
- **SSL/TLS**: Encrypted communication
- **Rate Limiting**: DoS protection
- **JWT**: API authentication
- **Security Headers**: XSS, clickjacking protection

## Resource Allocation

### Recommended (2 vCPU, 4GB RAM)

```
Component           │ Memory  │ CPU    │ Storage
────────────────────┼─────────┼────────┼──────────
Backend             │ ~300MB  │ ~15%   │ 100MB
PostgreSQL          │ ~500MB  │ ~10%   │ 2-5GB
Nginx               │ ~20MB   │ ~5%    │ 50MB
Prometheus          │ ~400MB  │ ~10%   │ 5-10GB
Grafana             │ ~200MB  │ ~5%    │ 500MB
Loki                │ ~300MB  │ ~5%    │ 3-5GB
Other (exporters)   │ ~100MB  │ ~5%    │ 100MB
────────────────────┼─────────┼────────┼──────────
OS & Overhead       │ ~1GB    │ ~15%   │ 5GB
────────────────────┼─────────┼────────┼──────────
TOTAL               │ ~2.8GB  │ ~70%   │ ~20GB
Available           │ ~1.2GB  │ ~30%   │ ~35GB
```

This allocation provides headroom for traffic spikes and future growth.

---

**Architecture designed for**: 10-20 concurrent users  
**Scalable to**: 100+ users with optimization  
**High Availability**: Can be enhanced with load balancer  
**Disaster Recovery**: Daily backups, 7-day retention
