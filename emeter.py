# Support for SMA Energy Meter.
# Copyright (c) 2026 transistorgrab@github.com 
# Licensed under the MIT License

import asyncio
import socket
import struct
import time
import logging

_LOGGER = logging.getLogger(__name__)

MCAST_GRP = '239.12.255.254'
MCAST_PORT = 9522

def get_local_ip() -> str:
    """Returns the active local IP address using the OS routing table."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1)) ## try to access some dummy address to load correct IP
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '0.0.0.0'
    finally:
        s.close()
    return local_ip

def is_valid_serial(serial: str):
    """Checks a serial number if it looks valid."""
    serial_str = str(serial).strip().zfill(10)
    return serial_str.isdigit() and len(serial_str) == 10

class SMAEmeterListener:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.data = {}
        self.transport = None
        self._task = None

    async def start(self):
        _LOGGER.info("[SMA Emeter] Starting UDP listener task...")
        loop = asyncio.get_running_loop()

        # Create UDP socket exakt wie im erfolgreichen Test-Skript
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            sock.bind(("", MCAST_PORT))
        except Exception as e:
            _LOGGER.error("Failed to bind UDP port %s: %s", MCAST_PORT, e)
            return

        # Join multicast group
        mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        self.sock = sock
        _LOGGER.info("[SMA Emeter] Successfully listening on %s:%s", MCAST_GRP, MCAST_PORT)

        # Background task to read packets continuously using the working executor pattern
        async def listen():
            last_update = 0
            while True:
                try:
                    data, addr = await loop.run_in_executor(None, self.sock.recvfrom, 2048)
                    
                    # Parse data and get serial
                    serial_str = self.parse(data)
                    
                    if serial_str:
                        now = time.time()
                        interval = self.entry.options.get('update_interval', 1.0)
                        if now - last_update >= interval:
                            for entity in self.hass.data.get("sma_emeter_entities", []):
                                if getattr(entity, 'serial_number', None) == serial_str:
                                    entity.async_write_ha_state()
                            last_update = now
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    _LOGGER.error("UDP receive error: %s", e)
                    await asyncio.sleep(1)

        self._task = self.hass.loop.create_task(listen())

    def async_stop(self):
        """Clean up socket and task on shutdown/reload."""
        if self._task:
            self._task.cancel()
        if hasattr(self, 'sock'):
            try:
                self.sock.close()
            except Exception:
                pass

    def parse(self, data: bytes):
        if len(data) < 28 or data[:4] != b'SMA\x00':
            return None

        susy_id, serial_num = struct.unpack('>HI', data[18:24])
        serial_str = str(serial_num)

        if not is_valid_serial(serial_str):
            return None

        if serial_str not in self.data:
            self.data[serial_str] = {}

        p_import = 0.0
        p_export = 0.0
        l1_imp, l2_imp, l3_imp = 0.0, 0.0, 0.0
        l1_exp, l2_exp, l3_exp = 0.0, 0.0, 0.0
        e_imp_total, e_exp_total = 0.0, 0.0
        l1_imp_e, l2_imp_e, l3_imp_e = 0.0, 0.0, 0.0
        l1_exp_e, l2_exp_e, l3_exp_e = 0.0, 0.0, 0.0

        index = 28
        length = len(data)

        while index + 4 <= length:
            channel_id, data_type, _ = struct.unpack('>HBB', data[index:index+4])
            index += 4

            if data_type == 4 or data_type == 0:
                if index + 4 > length:
                    break
                watts = struct.unpack('>I', data[index:index+4])[0] / 10.0
                index += 4

                if   channel_id == 1:  p_import = watts
                elif channel_id == 2:  p_export = watts
                elif channel_id == 21: l1_imp = watts
                elif channel_id == 22: l1_exp = watts
                elif channel_id == 41: l2_imp = watts
                elif channel_id == 42: l2_exp = watts
                elif channel_id == 61: l3_imp = watts
                elif channel_id == 62: l3_exp = watts

            elif data_type == 8 or data_type == 6:
                if index + 8 > length:
                    break
                ws = struct.unpack('>Q', data[index:index+8])[0]
                kwh = ws / 3600000.0
                index += 8

                if   channel_id == 1 : e_imp_total = kwh
                elif channel_id == 2 : e_exp_total = kwh
                elif channel_id == 21: l1_imp_e    = kwh
                elif channel_id == 22: l1_exp_e    = kwh
                elif channel_id == 41: l2_imp_e    = kwh
                elif channel_id == 42: l2_exp_e    = kwh
                elif channel_id == 61: l3_imp_e    = kwh
                elif channel_id == 62: l3_exp_e    = kwh
            else:
                break

        net_total = p_import - p_export

        self.data[serial_str]["power import"]       = p_import
        self.data[serial_str]["power export"]       = p_export
        self.data[serial_str]["power netto"]        = net_total
        self.data[serial_str]["power L1"]           = l1_imp - l1_exp
        self.data[serial_str]["power L2"]           = l2_imp - l2_exp
        self.data[serial_str]["power L3"]           = l3_imp - l3_exp
        self.data[serial_str]["energy imported"]    = e_imp_total
        self.data[serial_str]["energy exported"]    = e_exp_total
        self.data[serial_str]["energy L1 imported"] = l1_imp_e
        self.data[serial_str]["energy L2 imported"] = l2_imp_e
        self.data[serial_str]["energy L3 imported"] = l3_imp_e
        self.data[serial_str]["energy L1 exported"] = l1_exp_e
        self.data[serial_str]["energy L2 exported"] = l2_exp_e
        self.data[serial_str]["energy L3 exported"] = l3_exp_e

        return serial_str