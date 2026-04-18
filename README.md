# ⬡ SDN Network Utilization Monitor

Real-time per-port bandwidth monitoring using **Ryu SDN Controller** and **Mininet** network emulator.

---

## Overview

This project implements a real-time Network Utilization Monitor that leverages the Ryu SDN Framework and Mininet to collect, compute, and visualize per-port bandwidth statistics across virtual switches.

The system polls OpenFlow port statistics every 5 seconds, calculates RX/TX throughput in Mbps, and exposes the data via a REST API. Two dashboard interfaces consume the API and render live bandwidth metrics.

---

## Project Structure

```
network_monitor/
├── monitor_app.py      # Ryu SDN controller app — collects stats, serves REST API
├── topology.py         # Mininet 2-switch 4-host topology
├── dashboard.html      # Browser-based live dashboard (HTML/JS)
└── dashboard_2.py      # Terminal dashboard with coloured ASCII bandwidth bars
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│  Management Plane    HTML Dashboard / Python CLI     │
│                      (polls /stats/bandwidth)        │
└──────────────────────────┬──────────────────────────┘
                           │ HTTP REST (port 8080)
┌──────────────────────────▼──────────────────────────┐
│  Control Plane       Ryu Controller (monitor_app.py) │
│                      computes bandwidth, serves API  │
└──────────────────────────┬──────────────────────────┘
                           │ OpenFlow 1.3 (port 6633)
┌──────────────────────────▼──────────────────────────┐
│  Data Plane          Mininet OVS Switches (s1, s2)   │
│                      forward packets, report stats   │
└─────────────────────────────────────────────────────┘
```

---

## Network Topology

```
h1 (10.0.0.1) ──┐            ┌── h3 (10.0.0.3)
                 ├── s1 ── s2 ┤
h2 (10.0.0.2) ──┘            └── h4 (10.0.0.4)

Controller: c0 (Ryu) @ 127.0.0.1:6633
```

| Node | Type | IP Address | Connected To |
|------|------|-----------|--------------|
| h1 | Host | 10.0.0.1 | s1 (Port 1) |
| h2 | Host | 10.0.0.2 | s1 (Port 2) |
| h3 | Host | 10.0.0.3 | s2 (Port 1) |
| h4 | Host | 10.0.0.4 | s2 (Port 2) |
| s1 | OVS Switch (OpenFlow13) | — | h1, h2, s2 (trunk) |
| s2 | OVS Switch (OpenFlow13) | — | h3, h4, s1 (trunk) |
| c0 | Ryu Remote Controller | 127.0.0.1:6633 | s1, s2 |

---

## Prerequisites

- Python 3
- [Ryu SDN Framework](https://ryu-sdn.org/)
- [Mininet](http://mininet.org/)
- Open vSwitch (OVS)

Install dependencies:
```bash
pip install ryu requests
sudo apt-get install mininet
```

---

## How to Run

### Step 1 — Start the Ryu Controller (Terminal 1)
```bash
ryu-manager monitor_app.py ryu.app.simple_switch_13 --observe-links
```

### Step 2 — Start the Mininet Topology (Terminal 2)
```bash
sudo python3 topology.py
```

### Step 3 — Generate Traffic (Mininet CLI)
```bash
mininet> pingall
mininet> iperf h1 h3
```

### Step 4a — Open the Browser Dashboard
Open `dashboard.html` in any browser.

### Step 4b — Run the Terminal Dashboard (Terminal 3)
```bash
python3 dashboard_2.py
```

---

## REST API Reference

The Ryu controller exposes a REST API on `http://127.0.0.1:8080`.

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/stats/bandwidth` | GET | Per-port RX/TX bandwidth for all switches | JSON object keyed by `sw{id}_port{no}` |
| `/stats/switches` | GET | List of connected switch datapath IDs | JSON array of dpid integers |

**Sample response from `/stats/bandwidth`:**
```json
{
  "sw1_port1": {
    "switch": 1,
    "port": 1,
    "rx_mbps": 0.452,
    "tx_mbps": 0.231
  }
}
```

---

## Configuration Parameters

| Parameter | File | Default | Description |
|-----------|------|---------|-------------|
| `POLL_INTERVAL` | `monitor_app.py` | 5 seconds | How often the controller requests port stats |
| `REFRESH_INTERVAL` | `dashboard_2.py` | 5 seconds | How often the terminal dashboard rerenders |
| `setInterval` delay | `dashboard.html` | 5000 ms | How often the browser polls the API |
| `API_URL` | `dashboard_2.py` | `http://127.0.0.1:8080/stats/bandwidth` | REST API endpoint |
| Controller IP:Port | `topology.py` | `127.0.0.1:6633` | Ryu controller address for Mininet |

---

## Bandwidth Calculation

Per-port throughput is computed from the delta between consecutive OpenFlow port statistics replies:

```
rx_mbps = (Δrx_bytes × 8) / Δtime / 1,000,000
tx_mbps = (Δtx_bytes × 8) / Δtime / 1,000,000
```

---

## Dashboard Features

**Browser Dashboard (`dashboard.html`)**
- Live KPI cards: Total RX, Total TX, Active Ports, Switch Count
- Per-switch port tables with RX/TX values in Kbps and inline load bars
- Live clock, poll counter, and last-update timestamp

**Terminal Dashboard (`dashboard_2.py`)**
- Coloured ASCII progress bars for RX load
  - 🟢 Green: < 50%
  - 🟡 Yellow: < 80%
  - 🔴 Red: ≥ 80%
- Graceful error handling for connection failures and timeouts

---

## Author

**Shreeranganath M Saravade**  
