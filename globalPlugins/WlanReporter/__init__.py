import os.path
import winsound
from ctypes import addressof, byref, pointer, wintypes

import globalPluginHandler
import addonHandler
import ui
import globalCommands
from . import wlanapi

MODULE_DIR = os.path.dirname(__file__)
addonHandler.initTranslation()

def play(fileName):
	path = os.path.join(MODULE_DIR, fileName)
	winsound.PlaySound(path, winsound.SND_ASYNC)

SECURITY_TYPE = {
	wlanapi.DOT11_AUTH_ALGO_80211_OPEN: _("No authentication (Open)"),
	wlanapi.DOT11_AUTH_ALGO_80211_SHARED_KEY: "WEP",
	wlanapi.DOT11_AUTH_ALGO_WPA: "WPA-Enterprise",
	wlanapi.DOT11_AUTH_ALGO_WPA_PSK: "WPA-PSK",
	wlanapi.DOT11_AUTH_ALGO_RSNA: "WPA2-Enterprise",
	wlanapi.DOT11_AUTH_ALGO_RSNA_PSK: "WPA2-PSK",
}

@wlanapi.WLAN_NOTIFICATION_CALLBACK
def notifyHandler(pData, pCtx):
	if pData.contents.NotificationSource != wlanapi.WLAN_NOTIFICATION_SOURCE_ACM:
		return
	if pData.contents.NotificationCode == wlanapi.wlan_notification_acm_connection_complete:
		ssid = wlanapi.WLAN_CONNECTION_NOTIFICATION_DATA.from_address(pData.contents.pData).dot11Ssid.SSID
		ui.message(_("Connected to {}").format(ssid.decode("utf-8")))
		play("connect.wav")
	elif pData.contents.NotificationCode == wlanapi.wlan_notification_acm_disconnected:
		ssid = wlanapi.WLAN_CONNECTION_NOTIFICATION_DATA.from_address(pData.contents.pData).dot11Ssid.SSID
		ui.message(_("Disconnected from {}").format(ssid.decode("utf-8")))
		play("disconnect.wav")
	elif pData.contents.NotificationCode == wlanapi.wlan_notification_acm_interface_arrival:
		ui.message(_("A wireless device has been enabled"))
		play("connect.wav")
	elif pData.contents.NotificationCode == wlanapi.wlan_notification_acm_interface_removal:
		ui.message(_("A wireless device has been disabled"))
		play("disconnect.wav")

def customResize(array, newSize):
	return (array._type_ * newSize).from_address(addressof(array))

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = globalCommands.SCRCAT_SYSTEM

	def __init__(self):
		super().__init__()
		self._negotiated_version = wintypes.DWORD()
		self._client_handle = wintypes.HANDLE()
		wlanapi.WlanOpenHandle(wlanapi.CLIENT_VERSION_WINDOWS_VISTA_OR_LATER, None, byref(self._negotiated_version), byref(self._client_handle))
		wlanapi.WlanRegisterNotification(self._client_handle, wlanapi.WLAN_NOTIFICATION_SOURCE_ACM, True, notifyHandler, None, None, None)

	def script_wlanStatusReport(self, gesture):
		wlan_ifaces = pointer(wlanapi.WLAN_INTERFACE_INFO_LIST())
		wlanapi.WlanEnumInterfaces(self._client_handle, None, byref(wlan_ifaces))

		if wlan_ifaces.contents.NumberOfItems == 0:
			ui.message(_("No wireless devices"))
			wlanapi.WlanFreeMemory(wlan_ifaces)
			return

		for i in customResize(wlan_ifaces.contents.InterfaceInfo, wlan_ifaces.contents.NumberOfItems):
			if i.isState != wlanapi.wlan_interface_state_connected:
				ui.message(_("No wireless connections"))
				continue

			wlan_available_network_list = pointer(wlanapi.WLAN_AVAILABLE_NETWORK_LIST())
			wlanapi.WlanGetAvailableNetworkList(self._client_handle, byref(i.InterfaceGuid), 0, None, byref(wlan_available_network_list))
			for n in customResize(wlan_available_network_list.contents.Network, wlan_available_network_list.contents.NumberOfItems):
				if n.Flags & wlanapi.WLAN_AVAILABLE_NETWORK_CONNECTED:
					ui.message(_("Connected to {}, signal {}%, security type {}").format(n.dot11Ssid.SSID.decode(), n.wlanSignalQuality, SECURITY_TYPE.get(n.dot11DefaultAuthAlgorithm)))
					break
			wlanapi.WlanFreeMemory(wlan_available_network_list)
		wlanapi.WlanFreeMemory(wlan_ifaces)
	script_wlanStatusReport.__doc__ = _("Reports the status of the wireless connection")

	def terminate(self):
		wlanapi.WlanCloseHandle(self._client_handle, None)
