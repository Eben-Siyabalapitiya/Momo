import time
import wifi_setup

time.sleep(15)

connected = False
for _ in range(4):
    if wifi_setup.is_online():
        connected = True
        break
    time.sleep(5)

if connected:
    wifi_setup.write_status("connected", ssid=wifi_setup.active_ssid(), ip=wifi_setup.current_ip())
else:
    wifi_setup.start_hotspot()
