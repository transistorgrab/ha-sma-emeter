# Support for SMA Energy Meter.
# Copyright (c) 2026 transistorgrab@github.com 
# Licensed under the MIT License

import asyncio
import socket
import struct
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.selector import(
        SelectSelector
        ,SelectSelectorConfig
        ,SelectSelectorMode
        ,SelectOptionDict
        ,NumberSelector
        ,NumberSelectorConfig
        ,NumberSelectorMode
        ,TextSelector
        ,TextSelectorConfig
        )
from .emeter import MCAST_GRP, MCAST_PORT, get_local_ip, is_valid_serial
from . import DOMAIN

class SMAEmeterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(config_entry):
        return SMAEmeterOptionsFlowHandler()
    
    async def _discover_meters(self, timeout: float):
        """Listen to the UDP multicast for a few seconds to harvest serial numbers."""
        serials  = set()

        # check if an already running instance is there, i.e. there is already a meter configured
        domain_data = self.hass.data.get(DOMAIN, {})
        for listener in domain_data.values():
            if hasattr(listener, 'data'):
                for key in listener.data.keys():
                    if is_valid_serial(key):
                        serials.add(str(key))

        if serials:
            return sorted(list(serials))

        ## no previous running integration, look for devices
        local_ip = get_local_ip()
        loop = asyncio.get_running_loop()
        
        class DiscoveryProtocol(asyncio.DatagramProtocol):
            def datagram_received(self, data, addr):
                # parsing logic to identify SMA packets
                if len(data) >= 28 and data[:4] == b'SMA\x00':
                    try:
                        _, serial_num = struct.unpack('>HI', data[18:24])
                        serials.add(str(serial_num))
                    except:
                        pass

        try:
            # socket to share the port with emeter.py listener if it's already running.
            transport, _ = await asyncio.wait_for(
                                    loop.create_datagram_endpoint(
                                        DiscoveryProtocol
                                        ,local_addr=("0.0.0.0", MCAST_PORT)
                                        )
                                        ,timeout=timeout
                                    )
            
            # Join the multicast group
            sock = transport.get_extra_info("socket")
            mreq = struct.pack("4s4s", socket.inet_aton(MCAST_GRP), socket.inet_aton(local_ip))
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            
            # Let the listener collect packets for 'timeout' seconds
            await asyncio.sleep(timeout)
            
            # Clean up the socket
            transport.close()
        except Exception:
            pass # Fail gracefully if network binding is temporarily unavailable

        # Return a sorted list of unique serial numbers found
        return sorted(list(serials))

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            serial_number   = user_input['serial_number'].strip()
            if is_valid_serial(serial_number):
                await self.async_set_unique_id(serial_number)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                        title=f"SMA E-Meter {serial_number}"
                        ,data={'serial_number': serial_number}
                        ,options={'update_interval': user_input['update_interval']}
                        )
            errors['base'] = 'invalid_serial'
        # find all E meter devices in the networ
        discovered_serials = await self._discover_meters(timeout=3.0)

        if discovered_serials:
            options      = [SelectOptionDict(value=s, label=s) for s in discovered_serials]
            serial_field = SelectSelector(
                                SelectSelectorConfig(
                                    options=options, mode=SelectSelectorMode.DROPDOWN)
                                )
        else:
            # Fallback to manual entry
            serial_field = TextSelector(TextSelectorConfig())

        # identify devices already in use
        current_entries    = self._async_current_entries()
        configured_serials = [entry.data.get('serial_number') for entry in current_entries]

        options = []
        unconfigured_serials = []

        for serial in discovered_serials:
            if serial in configured_serials:
                options.append(
                    SelectOptionDict(value=serial,label=f"⚠️ {serial} (already configured)")
                    )
            else:
                unconfigured_serials.append(serial)
                options.append(
                    SelectOptionDict(value=serial, label=serial)
                    )

        # if only one serial is found make it the default
        default_value = vol.UNDEFINED
        if len(unconfigured_serials) == 1:
            default_value = unconfigured_serials[0]

        data_schema = vol.Schema({ vol.Required('serial_number'
                                                ,default=default_value if not discovered_serials else discovered_serials[0])
                                                :serial_field
                                   ,vol.Optional('update_interval', default=1.0):
                                        NumberSelector(
                                            NumberSelectorConfig(min=0.5,max=60.0,step=0.1
                                                                 ,mode=NumberSelectorMode.BOX
                                                                 ,unit_of_measurement='s'
                                                                 )
                                        )
                                })

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

class SMAEmeterOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for the integration so users can reconfigure the interval."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            # Update the entry options without needing to recreate the entry
            return self.async_create_entry(title="", data=user_input)

        # Pre-fill the current interval 
        current_interval = self.config_entry.options.get("update_interval", 1.0)
        
        return self.async_show_form(
                        step_id='init'
                        ,data_schema=vol.Schema({
                            vol.Required("update_interval", default=current_interval):
                                NumberSelector(
                                    NumberSelectorConfig(min=0.5,max=60.0,step=0.1
                                                        ,mode=NumberSelectorMode.BOX
                                                        ,unit_of_measurement="s"
                                                        )
                                    )
                                })
                        )
        