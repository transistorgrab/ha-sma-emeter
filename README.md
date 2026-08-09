# Home Assistant SMA Energy Meter Integration

This integration provides Home Assitant access to a SMA Energy Meter that is in the same network.
The Energy Meter broadcasts its measurement via UTP about every 200 ms.
This integration will allow to update the push rate to Home Assistant between 500 ms and 60 s to allow for lower system load and flexibility for plant control.

SMA Energy Meter integration provides theses measurements:

* Power import: Power over all three phases imported in W. 0 when export is higher than consumption
* Power export: Power over all three phases imported in W. 0 when import is higher than production
* Power netto: Power over all three phases in W. Negative when total **export** is higher than total import.
* Power L1: Power for first phase in W. Negative when exporting
* Power L2: Power for second phase in W. Negative when exporting
* Power L3: Power for third phase in W. Negative when exporting
* Energy imported: Total number of imported energy in kWh.
* Energy exported: Total number of exported energy in kWh.
* Energy L1 imported: Imported energy for first phase in kWh.
* Energy L2 imported: Imported energy for second phase in kWh.
* Energy L3 imported: Imported energy for third phase in kWh.
* Energy L1 exported: Exported energy for first phase in kWh.
* Energy L2 exported: Exported energy for second phase in kWh.
* Energy L3 exported: Exported energy for third phase in kWh.

This integration is provided as is.
It was tested with a SMA Energy Meter (first generation).
It wil most probably not work with a SMA Energy Meter 2.0 or a SMA Home Manager.
