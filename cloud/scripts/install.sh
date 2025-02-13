function main() {
    show_readme
    # install libvirt
    echo "Installing libvirt"
    install_libvirt
    # check_iommu
    echo "Checking IOMMU"
    check_iommu
    # check prime select and pci
    echo "Checking prime select and pci"
    check_prime_select
    # check pci
    check_pci
    get_pci
    bind_pci
    echo "Download cloud image"
    # download cloud image
    download_cloud_image jammy-server-cloudimg-amd64.img http://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img 50G
    echo "Install kvm and startup kvm"
    # install kvm
    read -p "Enter the number of vcpu in the KVM: " vcpu
    read -p "Enter the memory size in the KVM: " memory
    read -p "Enter the ssh port in the KVM: " ssh_port
    install_kvm $vcpu $memory
    # auto start kvm
    kvm_auto_startup ubuntu220405
    echo "Config host docker"
    # config host docker
    config_host_docker
    echo "Config iptables and please configure the port forwarding in the router to your host IP and SSH port"
    # config iptables
    config_iptables $ssh_port
}

main

function show_readme() {
    echo "Please read the README.md file for more information"
    echo "This KVM installation require the following setting in the host machine"
    echo "1. Enable IOMMU in host machine's BIOS"
    echo "2. Enable AMD (AMD-V/AMD-Vi) or Intel (VT-x/VT-d) virtualization in host machine's BIOS"
    echo "3. The host machine should at least have two GPUs (one iGPU and one or more NVIDIA dGPU), one iGPU for host and one or more NVIDIA dGPU for KVM"
    echo "4. The host machine should not connect to the monitor via NVIDIA GPU and should connect to the monitor via iGPU"
    echo "5. Installing NVIDIA driver in the host machine is not recommended"
    echo "6. All the NVIDIA dGPU should be bound to vfio-pci driver and will be used in KVM"
    echo "7. The host machine should have a stable internet connection with at least 100Mbps download speed"
    echo "8. The host machine should have at least 8 CPU cores"
    echo "9. The host machine should have at least 16GB of RAM"
    echo "10. The host machine should have at least 100GB of free disk space"
    echo "11. The host machine OS only support the Linux OS and should be newer than Ubuntu 22.04 LTS distribution"
    echo "12. The same Nvidia dGPU (video/audio PCIe) should be in the same IOMMU group"
    read -n 1 -s -r -p "Press any key to continue..."
}

function install_libvirt() {
    sudo apt update
    sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virtinst virt-manager cloud-utils
    sudo systemctl enable libvirtd
    sudo systemctl start libvirtd
    sudo usermod -aG libvirt $USER
    sudo usermod -aG kvm $USER
}

function check_prime_select() {
    local prime_select
    prime_select=$(prime-select query)
    if [ "$prime_select" = "nvidia" ] || [ "$prime_select" = "on-demand" ]; then
      echo "Prime select is set to nvidia"
      echo "Switching to intel"
      sudo prime-select intel
      read -n 1 -s -r -p "Press any key to reboot the system..."
      sudo sudo reboot
    else
      echo "Prime select is set to $prime_select"
      echo "There is no NVIDIA driver installed or started"
      echo "Processing the installation"
    fi
}

function download_cloud_image() {
    local image=$1
    local url=$2
    local file_size=$3
    cd /var/lib/libvirt/images || exit

    if [ ! -f $image ]; then
      echo "Downloading $image"
      wget $url -O $image
    else
      echo "$image already exists"
    fi
    sudo qemu-img create -b jammy-server-cloudimg-amd64.img -f qcow2 -F qcow2 ubuntu220405.qcow2 $file_size
}

function check_iommu() {
    local iommu
    iommu=$(dmesg | grep -i iommu)
    if [ -z "$iommu" ]; then
      echo "IOMMU is not enabled"
      echo "Please enable IOMMU in BIOS"
      exit 1
    else
      echo "IOMMU is enabled"
    fi
}

function check_pci() {
    local driver
    driver=$(lspci -nnk -s $pci | grep -i driver | awk '{print $3}')
    if [ "$driver" = "nvidia" ]; then
      echo "GPU $pci is bound to nvidia driver"
    else
      echo "GPU $pci is bound to $driver driver"
    fi
}

# Loop through each PCI address
function get_pci() {
    # Extract PCI addresses and store them in a variable
    pci_addresses=$(lspci -nnk | grep NVIDIA | awk '{print $1}' | sed 's/^0000://')
    # Loop through each PCI address
    for pci in $pci_addresses; do
        echo "Processing PCI device: $pci"
        # You can add additional commands here to process each PCI address
    done
}

function bind_pci() {
    sudo modprobe -r nvidia_drm
    sudo modprobe -r nvidia_uvm
    sudo modprobe -r nvidia_modeset
    ## Load vfio
    sudo modprobe vfio
    sudo modprobe vfio_iommu_type1
    sudo modprobe vfio_pci
    # Loop through each PCI address
    for pci in $pci_addresses; do
        echo "Processing detach Nvidia PCI device: $pci"
        virsh nodedev-detach $pci
    done
}

function install_kvm() {
    vcpu=$1
    memory=$2

    encrypted_disk="/var/lib/libvirt/images/ubuntu220405_encrypted.qcow2"
    luks_disk="/var/lib/libvirt/images/ubuntu220405_luks.qcow2"

    # Create an encrypted disk
    # create_encrypted_disk $encrypted_disk $luks_disk

    cmd="sudo virt-install \
      --name ubuntu220405 \
      --memory ${memory} \
      --vcpus ${vcpu} \
      --cpu host \
      --disk path=/var/lib/libvirt/images/ubuntu220405.qcow2,format=qcow2,bus=virtio,size=40 \
      --os-variant ubuntu22.04 \
      --network network=default \
      --graphics vnc,listen=0.0.0.0 --noautoconsole \
      --cloud-init user-data=user-data.yaml,meta-data=meta-data.yaml,network-config=network-config.yaml \
      --noautoconsole --noreboot --import"

    # Loop through the PCI addresses and add --host-device for each
    for pci in $pci_addresses; do
      cmd="$cmd --host-device $pci"
    done

    # Execute the command
    eval $cmd

    sudo virt-customize -a ubuntu220405.qcow2 --root-password password:1234

    sudo virt-customize -a ubuntu220405.qcow2 \
      --run-command "apt update && apt install -y ubuntu-drivers-common" \
      --run-command "ubuntu-drivers autoinstall" \
      --run-command "apt install -y nvidia-driver-550" \
      --run-command "apt install -y curl vim net-tools docker.io nvidia-docker" \
      --run-command "curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
      && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list" \
      --run-command "apt-get update && apt-get install -y nvidia-container-toolkit" \
      --run-command "awk '{ if (\$0 ~ /^ExecStart/) \$0=\"ExecStart=/usr/bin/dockerd -H unix:///var/run/docker.sock -H tcp://0.0.0.0:2375\"; print }' /lib/systemd/system/docker.service > /lib/systemd/system/docker.service" \
      --run-command "systemctl restart daemon-reload" \
      --run-command "systemctl restart docker" \
      --run-command "usermod -aG docker $USER"
}

function config_host_docker() {
    # config the host docker
    host_ip=$(virsh net-dhcp-leases default | grep -oP '\d+\.\d+\.\d+\.\d+')
    docker context create kvm --docker "host=tcp://$host_ip:2375"
    docker context use kvm
    # configure the IP forwarding
    echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward
    echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf
}

function kvm_auto_startup() {
    local kvm_name=$1
    virsh start $kvm_name
    virsh autostart $kvm_name
}

function kvm_remove() {
    local kvm_name=$1
    virsh destroy $kvm_name
    virsh undefine $kvm_name
    sudo rm /var/lib/libvirt/images/$kvm_name.qcow2
}

function config_iptables() {
    host_ip=$(virsh net-dhcp-leases default | grep -oP '\d+\.\d+\.\d+\.\d+')
    ssh_port=$1
    sudo iptables -I FORWARD -o virbr0 -d  $host_ip -p tcp --dport $ssh_port -j ACCEPT
    sudo iptables -t nat -A OUTPUT -p tcp --dport $ssh_port -j DNAT --to $host_ip:$ssh_port
    sudo iptables -t nat -I PREROUTING -p tcp --dport $ssh_port -j DNAT --to $host_ip:$ssh_port
    sudo iptables -A FORWARD -p tcp -d $host_ip --dport $ssh_port -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT
}

function create_encrypted_disk() {
    encrypted_disk=$1
    luks_disk=$2
    disk_size=$3

    # Create a new qcow2 image
    sudo qemu-img create -f qcow2 $encrypted_disk $disk_size

    # Encrypt the qcow2 image with LUKS
    echo "Creating LUKS encrypted disk"
    sudo cryptsetup luksFormat $encrypted_disk

    # Open the LUKS encrypted disk
    sudo cryptsetup open $encrypted_disk luks_disk

    # Create a filesystem on the encrypted disk
    sudo mkfs.ext4 /dev/mapper/luks_disk

    # Close the LUKS encrypted disk
    sudo cryptsetup close luks_disk

    # Convert the encrypted disk to qcow2 format
    sudo qemu-img convert -f raw -O qcow2 $encrypted_disk $luks_disk
}

red() { echo -e "\e[31m$@\e[0m"; }
green() { echo -e "\e[32m$@\e[0m"; }
blue() { echo -e "\e[34m$@\e[0m"; }

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $@" | tee -a install.log
}