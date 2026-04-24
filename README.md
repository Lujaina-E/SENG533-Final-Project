# SENG 533 Final Project — TeaStore Performance Evaluation

**Group 24** | University of Calgary

Lujaina Eldelebshany · Mariam Ibrahim · Eeman Abid · Fatima Asif · Syril Jacob · Shaherier Khan

---

## Overview

This project evaluates the runtime performance of the [TeaStore](https://github.com/DescartesResearch/TeaStore) microservices benchmark application. We isolate and stress-test each core microservice individually to identify bottlenecks, then apply intensive stress and spike testing to the identified bottleneck.

**Services tested:** WebUI · Persistence · Authentication · Recommender · Image Provider · Registry

---

## Repository Structure

```
.
├── locustfile.py                   # WebUI load test
├── locust_auth.py                  # Authentication service load test
├── locust_image.py                 # Image Provider load test
├── locust_recommender.py           # Recommender service load test
├── locust_test.py                  # Round 2 tests (includes all services)
├── docker-compose-webui.yaml       # Full stack + monitoring deployment
├── docker-compose-image.yaml       # Image Provider isolated deployment
├── generate_image_graphs.py        # Graph generation for Image Provider results
├── run_image_tests.sh              # Automated image test runner
├── monitoring/
│   ├── prometheus.yml              # Prometheus scrape config
│   └── prometheus/                 # Prometheus data
├── test_persistence_service/
│   ├── docker-compose-persistence.yaml
│   ├── locust_persistence.py       # Persistence service load test
│   ├── run_persistence_tests.ps1   # Automated persistence test runner (Windows)
│   ├── seeding.ps1                 # Database seeding script
│   ├── plot_results.py             # Graph generation for persistence results
│   └── results_*/                  # Raw CSV output from Locust runs
└── results/                        # Collected results across all services
```

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Python 3.8+](https://www.python.org/)
- [Locust](https://locust.io/) — install via `pip install locust`

---

## Setup & Running Tests

### 1. WebUI Service (Primary Bottleneck Test)

Start the full TeaStore stack:

```bash
# Step 1: Start backing services and wait until healthy
docker-compose -f docker-compose-webui.yaml up -d db registry persistence
docker-compose -f docker-compose-webui.yaml ps   # repeat until all show healthy

# Step 2: Start remaining services
docker-compose -f docker-compose-webui.yaml up -d auth image recommender webui
```

Run the WebUI load test:

```bash
locust -f locustfile.py --host http://localhost:8080/tools.descartes.teastore.webui
```

Open [http://localhost:8089](http://localhost:8089) in a browser and use:
- Users: `10, 50, 100, 200`
- Spawn rate: `1, 5, 10, 20`
- Duration: 2 minutes per run (3 runs per configuration)

---

### 2. Persistence Service

```bash
cd test_persistence_service

# Start the persistence stack
docker-compose -f docker-compose-persistence.yaml up -d

# Seed the database (must return "Database is ready!")
./seeding.ps1

# Run automated tests across all load levels
./run_persistence_tests.ps1

# Generate graphs
python3 plot_results.py
```

---

### 3. Authentication Service

Use the same Docker stack as WebUI (step 1 above), then:

```bash
locust -f locust_auth.py --host http://localhost:8080/tools.descartes.teastore.webui
```

---

### 4. Recommender Service

Set up a virtual environment to avoid dependency conflicts:

```bash
python -m venv locust-env
locust-env\Scripts\activate          # Windows
pip install locust==2.15.1 urllib3==1.26.18 requests==2.31.0

locust -f locust_recommender.py --host http://localhost:8080/tools.descartes.teastore.webui
```

---

### 5. Image Provider Service

```bash
chmod +x run_image_tests.sh && ./run_image_tests.sh
```

Or manually:

```bash
docker-compose -f docker-compose-image.yaml up -d
locust -f locust_image.py --host http://localhost:8080/tools.descartes.teastore.webui
```

Use loads: users = `10, 25, 50, 100, 200`, spawn rate = `10`, duration = 2 minutes.

---

### 6. Monitoring (Prometheus + Grafana + cAdvisor)

```bash
docker-compose -f docker-compose-webui.yaml up -d prometheus cadvisor grafana
```

| Tool       | URL                      | Credentials       |
|------------|--------------------------|-------------------|
| Grafana    | http://localhost:3000    | admin / admin     |
| Prometheus | http://localhost:9090    | —                 |
| cAdvisor   | http://localhost:8082    | —                 |

Prometheus scrapes cAdvisor every 15 seconds. The "TeaStore Monitoring" Grafana dashboard shows real-time CPU, memory, and network usage per container.

---

## Load Test Parameters

| Users | Spawn Rate | Duration | Runs |
|-------|-----------|----------|------|
| 10    | 1         | 2 min    | 3    |
| 50    | 5         | 2 min    | 3    |
| 100   | 10        | 2 min    | 3    |
| 200   | 20        | 2 min    | 3    |

CPU/memory snapshots via `docker stats` were taken at 0:40, 1:10, and 1:40 into each run.

---

## Key Findings

| Service        | Utilization | Notable Behaviour |
|----------------|-------------|-------------------|


---

## Utilization Formula

```
Utilization = (Throughput × (Response_time / 1000)) / (1 + Throughput × (Response_time / 1000))
```

## Stress Test Parameters

| Users | Spawn Rate | Duration | Runs |
|-------|------------|----------|------|
| 10    | 2          | 2 min    | 3    |
| 25    | 5          | 2 min    | 3    |
| 50    | 10         | 2 min    | 3    |
| 75    | 10         | 2 min    | 3    |
| 100   | 10         | 2 min    | 3    |
| 150   | 10         | 2 min    | 3    |
| 200   | 10         | 2 min    | 3    |
| 250   | 10         | 2 min    | 3    |
| 300   | 15         | 2 min    | 3    |
| 400   | 15         | 2 min    | 3    |
| 500   | 25         | 5 min    | 3    |
| 1000  | 50         | 5 min    | 3    |

## Spike Test Parameters

| Users | Spawn Rate | Duration | Runs |
|-------|------------|----------|------|
| 100   | 10         | 3 min    | 3    |
| 1000  | 200        | 4 min    | 3    |
| 100   | 10         | 3 min    | 3    |
| 2000  | 300        | 4 min    | 3    |
| 100   | 10         | 3 min    | 3    |
| 3000  | 500        | 4 min    | 3    |
