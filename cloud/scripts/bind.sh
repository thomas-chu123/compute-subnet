export VIRSH_GPU_VIDEO=pci_0000_01_00_0
export VIRSH_GPU_AUDIO=pci_0000_01_00_1

sudo modprobe -r nvidia_drm
sudo modprobe -r nvidia_uvm
sudo modprobe -r nvidia_modeset

## Load vfio
sudo modprobe vfio
sudo modprobe vfio_iommu_type1
sudo modprobe vfio_pci

## Unbind gpu from nvidia and bind to vfio
virsh nodedev-detach $VIRSH_GPU_VIDEO
virsh nodedev-detach $VIRSH_GPU_AUDIO
