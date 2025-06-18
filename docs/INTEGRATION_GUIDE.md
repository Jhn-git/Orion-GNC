# Orion GNC Integration Guide

This document defines the data flow, schemas, and integration points for the Orion GNC (Guidance, Navigation, and Control) system. It serves as a reference for developers working on services that interact with the GNC ecosystem.

## 1. Data Models

This section outlines the core data structures used for defining missions and transmitting real-time telemetry.

### 1.1. Mission Definition File (`mission.json`)

The `mission.json` file defines all parameters for a flight mission. It is submitted by the Mission Control UI and processed by the Mission Sequencer.

**Schema:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Orion Mission",
  "type": "object",
  "required": ["mission_id", "flight_plan"],
  "properties": {
    "mission_id": {
      "type": "string",
      "description": "Unique identifier for the mission.",
      "pattern": "^[a-zA-Z0-9_-]+$"
    },
    "flight_plan": {
      "type": "array",
      "description": "Sequence of waypoints defining the flight path.",
      "items": {
        "type": "object",
        "required": ["latitude", "longitude", "altitude", "hold_time_s"],
        "properties": {
          "latitude": {
            "type": "number",
            "minimum": -90,
            "maximum": 90
          },
          "longitude": {
            "type": "number",
            "minimum": -180,
            "maximum": 180
          },
          "altitude": {
            "type": "number",
            "description": "Altitude in meters.",
            "minimum": 0
          },
          "hold_time_s": {
            "type": "integer",
            "description": "Time to hold at the waypoint in seconds.",
            "minimum": 0
          }
        }
      }
    }
  }
}
```

### 1.2. Telemetry Data Packet

Telemetry data is transmitted by the GNC Flight Control service in a compact, real-time format.

**Format:**
```json
{
  "timestamp": "2023-10-27T10:00:00Z",
  "position": {
    "latitude": 34.0522,
    "longitude": -118.2437,
    "altitude": 150.5
  },
  "velocity": {
    "x": 10.2,
    "y": 5.1,
    "z": -1.5
  },
  "attitude": {
    "pitch": 5.0,
    "roll": 0.5,
    "yaw": 90.1
  },
  "status": "NOMINAL"
}
```

## 2. Redis Pub/Sub Channels

Services communicate asynchronously via Redis Pub/Sub channels. The following channels are defined:

### 2.1. `mission_queue`

Used by the Mission Control UI to submit new missions to the Mission Sequencer.

*   **Channel:** `mission_queue`
*   **Message Schema:** The message is a JSON string matching the [`mission.json`](#11-mission-definition-file-missionjson) schema.

### 2.2. `mission_status`

Used by the Mission Sequencer to broadcast status updates for ongoing missions.

*   **Channel:** `mission_status`
*   **Message Schema:**
    ```json
    {
      "mission_id": "mission-alpha-1",
      "status": "IN_PROGRESS",
      "timestamp": "2023-10-27T10:01:00Z",
      "details": "Executing waypoint 2 of 5."
    }
    ```

### 2.3. `telemetry_data`

Used by the GNC Flight Control service to stream real-time telemetry to the Telemetry Dashboard.

*   **Channel:** `telemetry_data`
*   **Message Schema:** The message is a JSON string matching the [Telemetry Data Packet](#12-telemetry-data-packet) format.

### 2.4. `gnc_commands`

Used by the Mission Sequencer to send discrete flight commands to the GNC Flight Control service.

*   **Channel:** `gnc_commands`
*   **Message Schema:**
    ```json
    {
      "command": "SET_WAYPOINT",
      "payload": {
        "latitude": 34.0522,
        "longitude": -118.2437,
        "altitude": 200.0
      },
      "timestamp": "2023-10-27T10:02:00Z"
    }
    ```

## 3. Service Integration Points

This section describes how the services interact with each other and with Redis.

### 3.1. Mission Control UI -> Mission Sequencer

1.  The user finalizes a mission in the **Mission Control UI**.
2.  The UI validates the mission against the [`mission.json`](#11-mission-definition-file-missionjson) schema.
3.  The UI serializes the mission object to a JSON string and publishes it to the [`mission_queue`](#21-mission_queue) channel on Redis.

### 3.2. Mission Sequencer -> GNC Flight Control

1.  The **Mission Sequencer** listens for new messages on the [`mission_queue`](#21-mission_queue) channel.
2.  Upon receiving a mission, it begins processing the `flight_plan` waypoints sequentially.
3.  For each waypoint, the Sequencer constructs a `SET_WAYPOINT` command and publishes it to the [`gnc_commands`](#24-gnc_commands) channel.
4.  It continuously publishes mission progress to the [`mission_status`](#22-mission_status) channel.

### 3.3. GNC Flight Control -> Telemetry Dashboard

1.  The **GNC Flight Control** service subscribes to the [`gnc_commands`](#24-gnc_commands) channel to receive flight instructions.
2.  During flight, it continuously generates telemetry data.
3.  It serializes the telemetry data into JSON packets and publishes them to the [`telemetry_data`](#23-telemetry_data) channel.
4.  The **Telemetry Dashboard** subscribes to this channel and visualizes the incoming data in real-time.

### 3.4. Service Connectivity to Redis

All services connect to a central Redis instance. Connection details (host, port, password) should be provided via environment variables. Services must implement robust reconnection logic to handle network interruptions.