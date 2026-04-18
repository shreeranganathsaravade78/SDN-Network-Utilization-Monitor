import requests
import time
import os
import sys

API_URL = "http://127.0.0.1:8080/stats/bandwidth"



#Time intervel
REFRESH_INTERVAL = 5





def make_bar(kbps, width=20):
    ratio = min(float(kbps) / 1000.0, 1.0)
    filled = int(ratio * width)
    empty  = width - filled
    if ratio < 0.5:
        bar = "\033[92m" + "█" * filled + "░" * empty + "\033[0m"
    elif ratio < 0.8:
        bar = "\033[93m" + "█" * filled + "░" * empty + "\033[0m"
    else:
        bar = "\033[91m" + "█" * filled + "░" * empty + "\033[0m"
    return bar

def display():
    iteration = 0
    while True:
        os.system('clear')
        iteration += 1

        print("\033[1;36m" + "═" * 72 + "\033[0m")
        print("\033[1;36m   ⬡  SDN NETWORK UTILIZATION MONITOR\033[0m")
        print("\033[1;36m" + "═" * 72 + "\033[0m")
        print(f"  \033[90mTime    :\033[0m \033[97m{time.strftime('%Y-%m-%d  %H:%M:%S')}\033[0m")
        print(f"  \033[90mRefresh :\033[0m \033[97mevery {REFRESH_INTERVAL}s\033[0m   "
              f"\033[90mPoll\033[0m \033[96m#{iteration}\033[0m")
        print(f"  \033[90mAPI     :\033[0m \033[96m{API_URL}\033[0m")
        print("\033[1;36m" + "═" * 72 + "\033[0m")

        try:
            resp = requests.get(API_URL, timeout=3)
            resp.raise_for_status()
            data = resp.json()

            if not data:
                print("\n  \033[93m[Waiting] No data yet — generate traffic in Mininet\033[0m")
                print("  \033[90mTry: mininet> iperf h1 h3\033[0m")
            else:
                switches = {}
                for key, val in data.items():
                    sw = "Switch {}".format(val["switch"])
                    if sw not in switches:
                        switches[sw] = []
                    switches[sw].append(val)

                total_rx = sum(v["rx_mbps"] * 1000 for v in data.values())
                total_tx = sum(v["tx_mbps"] * 1000 for v in data.values())

                print(f"  \033[90mTotal RX:\033[0m \033[96m{total_rx:>12.3f} Kbps\033[0m   "
                      f"\033[90mTotal TX:\033[0m \033[92m{total_tx:>12.3f} Kbps\033[0m   "
                      f"\033[90mSwitches:\033[0m \033[97m{len(switches)}\033[0m")
                print("\033[1;36m" + "─" * 72 + "\033[0m")

                for sw_name, ports in sorted(switches.items()):
                    print(f"\n  \033[1;97m● {sw_name.upper()}\033[0m  \033[92m● ONLINE\033[0m")
                    print("  " + "─" * 68)
                    print(f"  \033[90m{'PORT':<16} {'RX (Kbps)':>12} {'TX (Kbps)':>12}   {'RX LOAD':<22}\033[0m")
                    print("  " + "─" * 68)

                    for port in sorted(ports, key=lambda x: x["port"]):
                        port_no = port["port"]
                        rx_k = port["rx_mbps"] * 1000
                        tx_k = port["tx_mbps"] * 1000

                        if port_no == 4294967294:
                            label = "LOCAL (sys)"
                            dot   = "\033[90m●\033[0m"
                        else:
                            label = "Port {}".format(port_no)
                            dot   = "\033[92m●\033[0m"

                        bar = make_bar(rx_k)
                        print(f"  {dot} \033[97m{label:<14}\033[0m "
                              f"\033[96m{rx_k:>12.3f}\033[0m "
                              f"\033[92m{tx_k:>12.3f}\033[0m   {bar}")
                    print()

        except requests.exceptions.ConnectionError:
            print("\n  \033[91m[ERROR] Cannot reach Ryu controller.\033[0m")
            print("  \033[90mRun in Terminal 1:\033[0m")
            print("  \033[93mryu-manager monitor_app.py ryu.app.simple_switch_13 --observe-links\033[0m")
        except requests.exceptions.Timeout:
            print("\n  \033[91m[ERROR] Request timed out.\033[0m")
        except Exception as e:
            print(f"\n  \033[91m[ERROR] {e}\033[0m")

        print("\033[1;36m" + "═" * 72 + "\033[0m")
        print(f"  \033[90mUpdated: {time.strftime('%H:%M:%S')}  |  Press Ctrl+C to stop\033[0m")
        print("\033[1;36m" + "═" * 72 + "\033[0m")

        time.sleep(REFRESH_INTERVAL)

if __name__ == '__main__':
    try:
        display()
    except KeyboardInterrupt:
        print("\n\n  \033[93mDashboard stopped.\033[0m\n")
        sys.exit(0)
