# 🚀 Orion GNC - Autonomous Mission Operations System

## 1. 🎯 Project Overview

The **Orion GNC** project is a sophisticated, autonomous mission operations system that demonstrates enterprise-grade aerospace software engineering practices. At its core is the **Mission Sequencer**, an intelligent orchestration engine that transforms high-level mission plans into precise, real-time flight operations.

### 🔧 Key Components:

*   **Mission Sequencer:** The central brain that orchestrates autonomous missions using schema-driven validation and Redis Pub/Sub for real-time coordination
*   **GNC Flight Control:** A robust command executor that interfaces with Kerbal Space Program (KSP) for precision flight operations
*   **Mission Plan Builder:** Professional-grade UI for designing, validating, and monitoring complex mission sequences
*   **Live Telemetry Dashboard:** Real-time web dashboard for monitoring critical flight data and system status
*   **AI Post-Mission Analyst:** Advanced AI-powered tool for natural language analysis of mission performance

This system showcases advanced software engineering principles including test-driven development, microservices architecture, and autonomous system orchestration. Designed to demonstrate professional-grade capabilities to aerospace and defense industry leaders.

## 2. 🏗️ System Architecture

The Orion GNC system employs a sophisticated autonomous architecture centered around the **Mission Sequencer** as the mission director. The system operates as a collection of specialized microservices that communicate through Redis Pub/Sub messaging and API gateways.

### ⭐ Architecture Highlights:

*   **Mission Sequencer:** Acts as the central brain, validating mission plans against JSON schemas and orchestrating command sequences
*   **Schema-Driven Validation:** Ensures mission integrity through formal contract validation using [`mission_plan_schema.json`](docs/schemas/mission_plan_schema.json:1)
*   **Real-Time Coordination:** Redis Pub/Sub enables seamless communication between services with live status broadcasting
*   **API Gateway Pattern:** UI server acts as a centralized proxy, simplifying frontend communication and improving security
*   **Autonomous Operation:** Mission Sequencer directs operations while GNC Flight Control executes commands with full autonomy

The architecture promotes enterprise-grade principles: modularity, scalability, testability, and fault tolerance.

For a detailed breakdown of the components and data flow, please see the [**System Architecture Document**](docs/ARCHITECTURE.md:1) and the [**Mission Analysis Architecture**](docs/MISSION_ANALYSIS.md:1).

## 3. 🧪 Test-Driven Development

The Orion GNC system employs comprehensive test-driven development practices, ensuring reliability and maintainability at the professional level.

### 🔬 Test Suite Components:

*   **Unit Tests:** [`test_mission_sequencer.py`](mission-sequencer/test_mission_sequencer.py:1) - Comprehensive testing of Mission Sequencer functionality using `pytest` and `fakeredis`
*   **Integration Tests:** [`integration-test.py`](integration-test.py:1) - End-to-end system validation testing the complete workflow
*   **Mock Services:** Sophisticated mocking strategies for Redis and external dependencies
*   **Coverage Analysis:** Detailed test coverage reporting to ensure code quality

### 🏃 Running Tests:

```bash
# Run Mission Sequencer unit tests
cd mission-sequencer
pip install -r test_requirements.txt
pytest test_mission_sequencer.py -v

# Run integration tests
python integration-test.py
```

## 4. 📋 System Requirements

- Python 3.9+
- Redis
- Kerbal Space Program (v1.x)
- kRPC mod for KSP (v0.4.8 or later)
- A modern web browser
- pytest (for running test suite)

## 5. ⚙️ Setup and Installation

For detailed, step-by-step installation and configuration instructions, please refer to the [**Setup Guide**](docs/SETUP.md:1).

## 6. ⚡ Quick Start

### 🚀 Starting the Complete System:

```bash
# Start all services with Docker Compose
docker-compose up --build

# Access Mission Plan Builder
open http://localhost:5000

# Monitor telemetry
open http://localhost:5001
```

### 🎯 Running Sample Missions:

1. Load a sample mission from [`sample-missions/`](sample-missions/) directory
2. Validate the mission plan using the Mission Plan Builder
3. Execute the mission and monitor progress in real-time
4. Analyze results using the AI Post-Mission Analyst

## 7. 📱 Usage

### 6.1. 🎛️ Mission Plan Builder

The [Mission Plan Builder](mission-control-ui/index.html:1) provides a professional-grade interface for designing and executing autonomous missions:

*   **Schema Validation:** Real-time validation against [`mission_plan_schema.json`](docs/schemas/mission_plan_schema.json:1)
*   **Sample Missions:** Pre-built mission templates including [`orbital-insertion.json`](sample-missions/orbital-insertion.json:1) and [`simple-ascent.json`](sample-missions/simple-ascent.json:1)
*   **Real-Time Status:** Live mission progress monitoring with Redis Pub/Sub updates
*   **Mission Control:** Start, monitor, and manage autonomous mission execution

### 6.2. 🤖 Mission Sequencer (Autonomous Operation)

The [Mission Sequencer](mission-sequencer/main.py:1) operates autonomously as the mission director:

*   **Schema-Driven Planning:** Validates mission plans and ensures operational integrity
*   **Command Orchestration:** Sequences and times command execution with precision
*   **Status Broadcasting:** Provides real-time mission status via Redis Pub/Sub
*   **Fault Tolerance:** Handles errors gracefully and provides detailed logging

### 6.3. 🛸 GNC Flight Control (Command Executor)

The [GNC Flight Control Service](gnc-flight-control/main.py:1) serves as the autonomous command executor:

*   **Command Processing:** Executes flight commands received from Mission Sequencer
*   **KSP Integration:** Direct interface with Kerbal Space Program via kRPC
*   **Autonomous Operation:** Requires no manual intervention once mission begins

### 6.4. 📊 Live Telemetry Dashboard

The [Telemetry Dashboard](telemetry-dashboard/index.html:1) provides comprehensive mission monitoring:

*   **Real-Time Data:** Live spacecraft telemetry and system status
*   **Mission Progress:** Visual indicators of mission phase and completion status
*   **Performance Metrics:** Critical flight parameters and system health

### 6.5. 🧠 AI Post-Mission Analyst

The [AI Post-Mission Analyst](ai-post-mission-analyst/main.py:1) provides intelligent mission analysis. For more details on its capabilities and integration, see the [**Mission Analysis Documentation**](docs/MISSION_ANALYSIS.md:1).

*   **Natural Language Queries:** Ask questions about mission performance in plain English.
*   **Log Analysis:** Comprehensive analysis of mission logs and telemetry data.
*   **Performance Insights:** AI-powered recommendations and observations.

## 8. 🐳 Docker Deployment

Deploy the complete Orion GNC autonomous system using Docker for production-ready operation:

### 7.1. 🚀 System Deployment:

```bash
# Deploy all microservices
docker-compose up --build
```

This orchestrates the complete system including:
- Mission Sequencer (autonomous mission director)
- GNC Flight Control (command executor)
- Mission Plan Builder UI with API Gateway
- Live Telemetry Dashboard
- Redis Pub/Sub message broker

### 7.2. 🌐 Service Access Points:

- **Mission Plan Builder:** `http://localhost:5000` - Design and execute autonomous missions
- **Telemetry Dashboard:** `http://localhost:5001` - Monitor real-time mission progress
- **Mission Sequencer API:** `http://localhost:5002` - Direct API access for advanced users

### 7.3. 🔄 Operational Workflow:

1. **Mission Planning:** Use Mission Plan Builder to design mission sequences
2. **Validation:** System automatically validates against mission schema
3. **Execution:** Mission Sequencer orchestrates autonomous operation
4. **Monitoring:** Real-time telemetry and status updates via dashboards
5. **Analysis:** Post-mission AI analysis for performance insights

### 7.4. 📈 Post-Mission Analysis:

```bash
# Run comprehensive mission analysis
docker-compose run --rm ai_post_mission_analyst
```

### 7.5. 🛑 System Shutdown:

```bash
# Graceful system shutdown
docker-compose down
```

## 9. 🔧 Troubleshooting

### 8.1. 🤖 Mission Sequencer Issues:

**Issue:** Mission validation fails
*   **Solution:** Verify mission plan conforms to [`mission_plan_schema.json`](docs/schemas/mission_plan_schema.json:1). Check console logs for specific validation errors.

**Issue:** Mission Sequencer not responding
*   **Solution:** Ensure Redis is running and accessible. Check Mission Sequencer logs for connection errors.

### 8.2. 🔗 System Integration Issues:

**Issue:** Telemetry Dashboard not updating
*   **Solution:** Verify Redis Pub/Sub is operational and GNC Flight Control is connected to KSP. Check WebSocket connections in browser console.

**Issue:** Commands not executing in KSP
*   **Solution:** Confirm Redis message broker is running, GNC service is connected, and kRPC mod is properly installed. Review [`mission_log.txt`](logs/) for detailed error analysis.

**Issue:** UI Server gateway errors
*   **Solution:** Ensure all backend services are running and accessible. Check UI server logs for proxy connection issues.

### 8.3. 🧪 Test Suite Issues:

**Issue:** Tests failing
*   **Solution:** Install test requirements with `pip install -r test_requirements.txt`. Ensure `fakeredis` is properly configured for unit tests.

## 10. 🏆 Professional Engineering Showcase

The Orion GNC system is a demonstration of enterprise-grade software engineering applied to the challenges of autonomous aerospace operations. It showcases a combination of sophisticated architecture, rigorous development practices, and a professional user experience.

### 💡 Key Technical Achievements:

*   **Autonomous Mission Orchestration:** The **Mission Sequencer** acts as an intelligent, autonomous director, validating mission plans against a formal schema and orchestrating operations in real-time. This represents the core of the system's autonomous capabilities.

*   **Enterprise-Grade Architecture:** The system employs a decoupled, scalable microservices architecture coordinated via a **Redis Pub/Sub message broker**. A UI server acting as an **API Gateway** provides a secure and simplified access point for frontend clients.

*   **Comprehensive Test-Driven Development (TDD):** The project's commitment to quality is demonstrated through a robust test suite, including **unit tests** ([`test_mission_sequencer.py`](mission-sequencer/test_mission_sequencer.py:1)) with `fakeredis` and end-to-end **integration tests** ([`integration-test.py`](integration-test.py:1)). This practice ensures reliability and maintainability.

*   **Professional-Grade Mission Operations UI:** The system features a sophisticated **Mission Plan Builder** and **Live Telemetry Dashboard**, providing a comprehensive interface for mission design, execution, and real-time monitoring.

*   **Production-Ready Deployment:** The entire system is containerized using **Docker** and orchestrated with `docker-compose.yml`, allowing for consistent, one-command deployment—a hallmark of modern, production-ready systems.
