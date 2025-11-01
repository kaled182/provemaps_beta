1. Sites
-----------

Sites represent the POPs or physical locations where equipment lives (for example: Goiania, Anapolis).

Steps:

- In Django Admin open **Sites -> Add**.
- Fill the fields:
  - **Name**: unique identifier for the location (e.g. `Goiania-POP`).
  - **City**: descriptive city name (e.g. `Goiania`).
  - **Latitude / Longitude** (optional): geographic coordinates.
  - **Description** (optional): additional notes about the site.

Example  
Name: Goiania-POP  
City: Goiania  
Latitude: -16.6869  
Longitude: -49.2648  
Description: Main PoP in Goiania

2. Devices
-----------

Devices are the network elements (switches, routers, etc.) that belong to a site.

Steps:

- In Django Admin open **Devices -> Add**.
- Fill the fields:
  - **Site**: select the previously created site (e.g. `Goiania-POP`).
  - **Name**: unique identifier inside the site (e.g. `SW-GYN-01`).
  - **Vendor**: manufacturer (e.g. `Cisco`, `Mikrotik`).
  - **Model**: hardware model (e.g. `C9500-24Q`).
  - **Zabbix host ID** (optional): identifier that matches the Zabbix host.

Example  
Site: Goiania-POP  
Name: SW-GYN-01  
Vendor: Cisco  
Model: C9500-24Q  
Zabbix host ID: 12345

3. Ports
-----------

Ports are the physical interfaces of a device (e.g. `Gi1/0/10`).

Steps:

- In Django Admin open **Ports -> Add**.
- Fill the fields:
  - **Device**: choose the owning device (e.g. `Goiania-POP - SW-GYN-01`).
  - **Name**: port label (e.g. `Gi1/0/10`).
  - **Zabbix item key** (optional): monitoring key in Zabbix (e.g. `net.if.in[Gi1/0/10]`).
  - **Notes** (optional): any remarks about the port.

Example  
Device: Goiania-POP - SW-GYN-01  
Name: Gi1/0/10  
Zabbix item key: net.if.in[Gi1/0/10]  
Notes: Uplink to Anapolis

4. Fiber cables
---------------

Fiber cables connect two ports (origin and destination).

Steps:

- In Django Admin open **Fiber Cables -> Add**.
- Fill the fields:
  - **Name**: unique link name (e.g. `GYN-ANA-01`).
  - **Origin port**: select the source port (e.g. `Goiania-POP - SW-GYN-01::Gi1/0/10`).
  - **Destination port**: select the destination port (e.g. `Anapolis-POP - SW-ANA-01::Gi0/0/1`).
  - **Length km** (optional): approximate length in kilometres.
  - **Path coordinates** (optional): JSON list of map points (fill only if you know them).
  - **Status**: current state (Operational, Unavailable, Degraded, Unknown).
  - **Notes** (optional): extra information about the cable.

Example  
Name: GYN-ANA-01  
Origin port: Goiania-POP - SW-GYN-01::Gi1/0/10  
Destination port: Anapolis-POP - SW-ANA-01::Gi0/0/1  
Length km: 55.30  
Status: Operational  
Notes: Direct fibre Goiania <-> Anapolis

5. Fiber events
---------------

Fiber events record changes in cable status (outage, restore, degraded, etc.).

Steps:

- In Django Admin open **Fiber Events -> Add**.
- Fill the fields:
  - **Fiber**: choose the affected cable (e.g. `GYN-ANA-01`).
  - **Timestamp**: event time (pre-filled automatically, but can be adjusted).
  - **Previous status**: status before the change (e.g. `up`).
  - **New status**: new status (e.g. `down`).
  - **Detected reason** (optional): cause (e.g. `Fiber cut`).

Example  
Fiber: GYN-ANA-01  
Timestamp: [auto]  
Previous status: up  
New status: down  
Detected reason: No light on transmitter

Summary of data entry order
---------------------------

1. Site - location that hosts the equipment.  
2. Device - network element inside the site.  
3. Port - interface that belongs to the device.  
4. Fiber cable - connection between two ports.  
5. Fiber event - history of cable status changes.
