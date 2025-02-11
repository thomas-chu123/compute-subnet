function main() {
    # install libvirt
    install_libvirt
    # check prime select and pci
    check_prime_select
    check_pci
    get_pci
    bind_pci
    # download cloud image
    download_cloud_image jammy-server-cloudimg-amd64.img http://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img 50G
    # install kvm
    install_kvm 4 8192
    # auto start kvm
    kvm_auto_startup ubuntu220405
    # config host docker
    config_host_docker
    # config iptables
    config_iptables 4444
}

main

function install_libvirt() {
    sudo apt update
    sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virtinst virt-manager
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