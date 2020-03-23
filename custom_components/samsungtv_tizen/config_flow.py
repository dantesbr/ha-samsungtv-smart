"""Config flow for Samsung TV."""
import socket
from urllib.parse import urlparse
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.config_entries import SOURCE_IMPORT

from homeassistant.components.ssdp import (
    ATTR_SSDP_LOCATION,
    ATTR_UPNP_MANUFACTURER,
    ATTR_UPNP_MODEL_NAME,
    ATTR_UPNP_UDN,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_ID,
    CONF_MAC,
    CONF_NAME,
    CONF_PORT,
    CONF_API_KEY,
)

# pylint:disable=unused-import
from . import SamsungTVInfo
from .const import (
    DOMAIN,
    DEFAULT_NAME,
    CONF_DEVICE_NAME,
    CONF_DEVICE_MODEL,
    CONF_UPDATE_METHOD,
    UPDATE_METHODS,
    RESULT_SUCCESS,
    RESULT_NOT_SUCCESSFUL,
)

DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str, vol.Required(CONF_NAME): str, vol.Optional(CONF_API_KEY): str})
_LOGGER = logging.getLogger(__name__)

def _get_ip(host):
    if host is None:
        return None
    return socket.gethostbyname(host)


class SamsungTVConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Samsung TV config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    # pylint: disable=no-member # https://github.com/PyCQA/pylint/issues/3167

    def __init__(self):
        """Initialize flow."""
        self._tvinfo = None
        self._host = None
        self._api_key = None
        self._name = None
        self._mac = None
        self._update_method = None

        self._title = None

    def _get_entry(self):
        data = {
            CONF_HOST: self._host,
            CONF_API_KEY: self._api_key,
            CONF_NAME: self._tvinfo._name,
            CONF_ID: self._tvinfo._uuid,
            CONF_MAC: self._mac,
            CONF_DEVICE_NAME: self._tvinfo._device_name,
            CONF_DEVICE_MODEL: self._tvinfo._device_model,
            CONF_PORT: self._tvinfo._port,
            CONF_UPDATE_METHOD: self._update_method
        }
        if self._api_key:
            CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL
        else:
            CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL
        
        _LOGGER.info("Configured new entity %s with host %s", self._title, self._host)
        return self.async_create_entry(title=self._title, data=data,)

    async def _try_connect(self, device_name = ""):
        """Try to connect and check auth."""
        self._tvinfo = SamsungTVInfo(self.hass, self._host, self._name)
        result = await self._tvinfo.get_device_info(self.hass.helpers.aiohttp_client.async_get_clientsession(), device_name, self._api_key)
        return result

    async def async_step_import(self, user_input=None):
        """Handle configuration by yaml file."""
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            ip_address = await self.hass.async_add_executor_job(
                _get_ip, user_input[CONF_HOST]
            )

            await self.async_set_unique_id(ip_address)
            self._abort_if_unique_id_configured()

            self._host = ip_address
            self._api_key = user_input.get(CONF_API_KEY)
            self._name = user_input.get(CONF_NAME)
            update_method = user_input.get(CONF_UPDATE_METHOD, "")
            if update_method:
                self._update_method = update_method
            elif self._api_key:
                self._update_method = UPDATE_METHODS["SmartThings"]
            else:
                self._update_method = UPDATE_METHODS["Ping"]
            device_name = user_input.get(CONF_DEVICE_NAME, "")
            is_import = user_input.get(SOURCE_IMPORT, False)
            
            result = await self._try_connect(device_name)
            
            if result != RESULT_SUCCESS:
                if is_import:
                    _LOGGER.error("Error during setup of host %s using configuration.yaml info. Reason: %s", ip_address, result)
                    return self.async_abort(reason=result)
                else:
                    return self._show_form({"base": result})
            
            mac = user_input.get(CONF_MAC, "")
            self._mac = mac if not self._tvinfo._macaddress else self._tvinfo._macaddress 

            self._title = self._tvinfo._name
            if self._api_key:
                self._title += " (SmartThings)"
            
            return self._get_entry()

        return self._show_form()

    @callback
    def _show_form(self, errors=None):
        """Show the form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors if errors else {},
        )

    # async def async_step_ssdp(self, user_input=None):
        # """Handle a flow initialized by discovery."""
        # host = urlparse(user_input[ATTR_SSDP_LOCATION]).hostname
        # ip_address = await self.hass.async_add_executor_job(_get_ip, host)
    
        # self._host = host
        # self._ip = self.context[CONF_IP_ADDRESS] = ip_address
        # self._manufacturer = user_input.get(ATTR_UPNP_MANUFACTURER)
        # self._model = user_input.get(ATTR_UPNP_MODEL_NAME)
        # self._name = f"Samsung {self._model}"
        # self._id = user_input.get(ATTR_UPNP_UDN)
        # self._title = self._model
    
        # # probably access denied
        # if self._id is None:
            # return self.async_abort(reason=RESULT_AUTH_MISSING)
        # if self._id.startswith("uuid:"):
            # self._id = self._id[5:]

        # await self.async_set_unique_id(ip_address)
        # self._abort_if_unique_id_configured(
            # {
                # CONF_ID: self._id,
                # CONF_MANUFACTURER: self._manufacturer,
                # CONF_MODEL: self._model,
            # }
        # )

        # self.context["title_placeholders"] = {"model": self._model}
        # return await self.async_step_confirm()

    # async def async_step_confirm(self, user_input=None):
        # """Handle user-confirmation of discovered node."""
        # if user_input is not None:
            # result = await self.hass.async_add_executor_job(self._try_connect)

            # if result != RESULT_SUCCESS:
                # return self.async_abort(reason=result)
            # return self._get_entry()

        # return self.async_show_form(
            # step_id="confirm", description_placeholders={"model": self._model}
        # )

    # async def async_step_reauth(self, user_input=None):
        # """Handle configuration by re-auth."""
        # self._host = user_input[CONF_HOST]
        # self._id = user_input.get(CONF_ID)
        # self._ip = user_input[CONF_IP_ADDRESS]
        # self._manufacturer = user_input.get(CONF_MANUFACTURER)
        # self._model = user_input.get(CONF_MODEL)
        # self._name = user_input.get(CONF_NAME)
        # self._title = self._model or self._name

        # await self.async_set_unique_id(self._ip)
        # self.context["title_placeholders"] = {"model": self._title}

        # return await self.async_step_confirm()