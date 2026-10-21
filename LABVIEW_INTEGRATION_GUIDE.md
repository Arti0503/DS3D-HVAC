# DS3D-HVAC — LabVIEW Integration & UDP Communication Guide

This document defines the exact network protocol, UDP port mapping, and JSON schemas for communication between **LabVIEW** and the **Unity DS3D-HVAC Simulator**.

---

## 1. Network Configuration

| Parameter | LabVIEW Side | Unity Side | Description |
| :--- | :--- | :--- | :--- |
| **Transmit Port (TX)** | Sends to **9000** | Sends to **5005** | UDP datagram transmission |
| **Receive Port (RX)** | Listens on **5005** | Listens on **9000** | UDP datagram reception |
| **Default IP** | `127.0.0.1` | `127.0.0.1` | Local loopback (or LAN IP) |
| **Encoding** | `UTF-8` | `UTF-8` | String payload encoding |

> **Note**: Unity automatically captures the IP address of incoming LabVIEW packets. When running over a LAN, as soon as LabVIEW sends its first packet to Unity, Unity will route its replies back to that sender IP on Port 5005.

---

## 2. Inbound Commands (LabVIEW $\rightarrow$ Unity, Port 9000)

LabVIEW can trigger faults, reset workflows, or skip steps. Unity accepts both structured JSON and raw integer strings.

### A. Trigger Fault by Code (Recommended JSON)
```json
{
  "command": "trigger_fault",
  "fault_code": 101
}
```
*Shorthand JSON also supported:*
```json
{
  "fault": 101
}
```

### B. Trigger Fault by Code (Raw String Fallback)
```text
101
```

### C. Reset Active Fault
Clears any active fault in Unity and returns the simulator to the idle inspection state:
```json
{
  "command": "reset"
}
```
*(Or plain text: `reset`)*

### D. Skip Current Step
Skips the current step in Easy/Training mode:
```json
{
  "command": "skip_step"
}
```
*(Or plain text: `skip`)*

### Registered HVAC Fault Codes
The HVAC project currently registers the following procedural faults:
- `101`: Primary Refrigeration & Compressor Diagnostics
- `102`: Evaporator Blower & Motor Inspection
- `103`: Condenser Fan & Heat Exchanger Servicing
- `104` to `114`: Additional Subsystem Overhaul & Procedure Training Scenarios

---

## 3. Outbound Telemetry (Unity $\rightarrow$ LabVIEW, Port 5005)

### Workflow & Attempt Counting Rules
1. **Wrong Tool Selected**:
   - Unity displays the warning in the 3D simulation.
   - **No network packet is sent** (maintains network quietness).
   - Unity increments the internal wrong attempt counter for that specific step.
2. **Correct Tool Selected & Step Accomplished**:
   - Unity executes the step animation/action.
   - Upon step completion, Unity immediately sends the `step_completed` JSON packet to LabVIEW on Port 5005.
3. **All Steps Completed**:
   - Unity sends the `fault_completed` summary packet with the wrong attempt counts for all steps.

---

### Payload 1: Step Accomplished (`step_completed`)
Sent whenever the user successfully completes a step with the correct tool:

```json
{
  "event": "step_completed",
  "fault_code": 101,
  "step_number": 1,
  "wrong_attempts": 0,
  "total_steps": 4,
  "status": "success",
  "is_fault_completed": false
}
```

#### Example: Step 2 completed after 2 wrong tool clicks:
```json
{
  "event": "step_completed",
  "fault_code": 101,
  "step_number": 2,
  "wrong_attempts": 2,
  "total_steps": 4,
  "status": "success",
  "is_fault_completed": false
}
```

#### Field Definitions
| Field | Type | Description |
| :--- | :--- | :--- |
| `event` | String | Always `"step_completed"` |
| `fault_code` | Integer | The active fault code (e.g. `101`) |
| `step_number` | Integer | 1-based index of the step just accomplished (`1`, `2`, `3`...) |
| `wrong_attempts`| Integer | Count of incorrect tool attempts made before completing this step |
| `total_steps` | Integer | Total number of steps in this fault procedure |
| `status` | String | Always `"success"` for completed steps |
| `is_fault_completed` | Boolean | `true` if this was the final step of the fault; otherwise `false` |

---

### Payload 2: Fault Completed Summary (`fault_completed`)
Sent when all steps of the procedure have been completed:

```json
{
  "event": "fault_completed",
  "fault_code": 101,
  "status": "success",
  "total_steps": 16,
  "total_mistakes": 0,
  "is_fault_completed": true,
  "compression_highlights": true,
  "arrows_active": true
}
```

#### Field Definitions
| Field | Type | Description |
| :--- | :--- | :--- |
| `event` | String | Always `"fault_completed"` |
| `fault_code` | Integer | The completed fault code (e.g. `101`) |
| `status` | String | Always `"success"` |
| `total_steps` | Integer | Total number of steps completed |
| `total_mistakes` | Integer (I32) | Total number of incorrect tool clicks made across all steps |
| `is_fault_completed` | Boolean | Always `true` |
| `compression_highlights` | Boolean | Restored back to `true` |
| `arrows_active` | Boolean | Restored back to `true` |

---

### Payload 3: Fault Started Acknowledgment (`fault_started`)
Sent immediately when a fault is activated in Unity (via LabVIEW command or UI click):

```json
{
  "event": "fault_started",
  "fault_code": 101,
  "total_steps": 4,
  "status": "started"
}
```

---

## 4. LabVIEW Native JSON Parsing Guide

In LabVIEW, use the **Unflatten From JSON** primitive (`Programming -> String -> Flatten/Unflatten String -> Unflatten From JSON`):

### Cluster for Fault Completed Summary (`fault_completed`)
To display the summary, create a Cluster containing:
- `event` (String Control) — `"fault_completed"`
- `fault_code` (Numeric Control, I32)
- `status` (String Control) — `"success"`
- `total_steps` (Numeric Control, I32)
- `total_mistakes` (Numeric Control, I32) — Total mistakes across the entire fault (single integer, not per-step)
- `is_fault_completed` (Boolean Control) — `true`

### Cluster for Step Progress (`step_completed`)
To track step-by-step progress, create a Cluster containing:
- `event` (String Control) — `"step_completed"`
- `fault_code` (Numeric Control, I32)
- `step_number` (Numeric Control, I32)
- `wrong_attempts` (Numeric Control, I32)
- `total_steps` (Numeric Control, I32)
- `status` (String Control)
- `is_fault_completed` (Boolean Control)

Wire the incoming UDP string into the **JSON String** input and unbundle the cluster to wire directly to your indicators.
