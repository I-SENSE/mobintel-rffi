#!/bin/bash

# Function to load module and get interface name
load_module_and_get_interface() {
    echo "Hello world"
    local module=$1
    echo "Loading module: $module"
    sudo modprobe $module

    # Wait a bit to ensure the interface is up
    sleep 2

    # Get the new interface name and return it
    iw dev | grep Interface | awk '{print $2}' | head -n 1
}

# Function to configure a wireless device based on its description
configure_wireless_device() {
    local device_info=$1

    local interface_name=""
    # Atheros - try common Atheros drivers
    if [[ $device_info == *"Atheros"* ]]; then
        sudo modprobe ath9k
        sudo modprobe ath5k
        sudo modprobe ath10k_pci
    # Intel - try common Intel drivers
    elif [[ $device_info == *"Intel"* ]]; then
        sudo modprobe iwlwifi
    # Broadcom - try common Broadcom drivers
    elif [[ $device_info == *"Broadcom"* ]]; then
        sudo modprobe wl
        sudo modprobe b43
    # Realtek - try common Realtek drivers
    elif [[ $device_info == *"Realtek"* ]]; then
        sudo modprobe rtl8723de
        sudo modprobe rtl8188ee
    # Qualcomm - try common Qualcomm drivers
    elif [[ $device_info == *"Qualcomm"* ]]; then
        sudo modprobe ath10k_pci
        sudo modprobe ath9k
    fi

    interface_name=$(iw dev | grep Interface | awk '{print $2}' | head -n 1)

    echo "Interface: $interface_name"

    # Check if interface name is obtained
    if [ -z "$interface_name" ]; then
        echo "Failed to obtain interface name."
        exit 1
    fi

    # Network configuration commands using $interface_name
    configure_network "$interface_name"
}

# Function to find and configure the first matching wireless device
configure_first_matching_device() {
    pci_devices=$(lspci | grep -i 'wireless' | grep -Ei 'Intel|Broadcom|Atheros|Qualcomm|Realtek')
    if [ -z "$pci_devices" ]; then
        echo "No recognized wireless device found."
        exit 1
    fi

    # Loop through each device and attempt to configure
    while read -r device; do
        echo "Found wireless device: $device"
        configure_wireless_device "$device"
        break  # Remove this line if you want to configure all detected devices
    done <<< "$pci_devices"
}

# Function to configure network
configure_network() {
    local ifname=$(iw dev | grep Interface | awk '{print $2}' | head -n 1)

    echo "Configuring network for interface $ifname..."
    sudo ip link set $ifname up
    sudo systemctl start network-manager
    sudo nmcli connection add type wifi con-name mobloc ifname $ifname mac $(cat /sys/class/net/$ifname/address) ssid mobloc_wlan mode infra ip4 192.168.16.2/24
    sudo nmcli con modify mobloc 802-11-wireless-security.key-mgmt wpa-psk wifi-sec.psk P@ssw0rd123
}

# Main
configure_first_matching_device


sudo ip link set wlp3s0 up
sudo systemctl start network-manager
sudo nmcli connection add type wifi con-name mobloc ifname wlp3s0 mac $(cat /sys/class/net/wlp3s0/address) ssid mobloc_wlan mode infra ip4 192.168.16.2/24
sudo nmcli con modify mobloc 802-11-wireless-security.key-mgmt wpa-psk wifi-sec.psk P@ssw0rd123

sudo ip link set wlp5s0 up
sudo systemctl start network-manager
sudo nmcli connection add type wifi con-name mobloc ifname wlp5s0 mac $(cat /sys/class/net/wlp5s0/address) ssid mobloc_wlan mode infra ip4 192.168.16.2/24
sudo nmcli con modify mobloc 802-11-wireless-security.key-mgmt wpa-psk wifi-sec.psk P@ssw0rd123