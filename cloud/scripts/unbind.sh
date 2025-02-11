export VIRSH_GPU_VIDEO=pci_0000_01_00_0
export VIRSH_GPU_AUDIO=pci_0000_01_00_1

virsh nodedev-reattach $VIRSH_GPU_VIDEO
virsh nodedev-reattach $VIRSH_GPU_AUDIO

## Unload vfio
sudo modprobe -r vfio_pci
sudo modprobe -r vfio_iommu_type1
sudo modprobe -r vfio

## Load nvidia
sudo modprobe nvidia_modeset
sudo modprobe nvidia_uvm
sudo modprobe nvidia_drm
