cd /var/lib/libvirt/images

sudo wget http://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img -O /var/lib/libvirt/images/jammy-server-cloudimg-amd64.img

sudo qemu-img create -b jammy-server-cloudimg-amd64.img -f qcow2 -F qcow2 ubuntu220405_1.qcow2 40G

sudo virt-install \
  --name ubuntu220405_1 \
  --memory 4096 \
  --vcpus 4 \
  --cpu host \
  --disk path=/var/lib/libvirt/images/ubuntu220405_1.qcow2,format=qcow2,bus=virtio,size=40 \
  --os-variant ubuntu22.04 \
  --network network=default \
  --graphics vnc,listen=0.0.0.0 --noautoconsole \
  --host-device 01:00.0 \
  --host-device 01:00.1 \
  --cloud-init user-data=user-data.yaml,meta-data=meta-data.yaml,network-config=network-config.yaml \
  --noautoconsole --noreboot
  --import

sudo virt-customize -a ubuntu220405_1.qcow2 --root-password password:1234

sudo virt-customize -a ubuntu220405_1.qcow2 \
  --run-command "apt update && apt install -y ubuntu-drivers-common" \
  --run-command "ubuntu-drivers autoinstall" \
  --run-command "apt install -y nvidia-driver-550" \
  --run-command "apt install -y curl vim net-tools docker.io nvidia-docker" \
  --run-command "curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list" \
  --run-command "apt-get update && apt-get install -y nvidia-container-toolkit"


sudo mkdir -p /etc/systemd/system/docker.service.d
sudo nano /etc/systemd/system/docker.service.d/override.conf
  [Service]
  ExecStart=
  ExecStart=/usr/bin/dockerd -H unix:///var/run/docker.sock -H tcp://0.0.0.0:2375

sudo nano /lib/systemd/system/docker.service
ExecStart=/usr/bin/dockerd -H unix:///var/run/docker.sock -H tcp://0.0.0.0:2375


sudo systemctl daemon-reload
sudo systemctl restart docker

docker context create kvm --docker "host=tcp://192.168.122.164:2375"
docker context use kvm

echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

virsh net-dhcp-leases default
