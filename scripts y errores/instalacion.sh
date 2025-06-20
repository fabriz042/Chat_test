#!/bin/bash
#chmod +x install-k8s.sh

echo "==================================="
echo "   INSTALADOR DE KUBERNETES"
echo "==================================="
echo

set -e

echo "==== Fase 1: Desactivar swap ===="
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab

echo "==== Fase 2: Habilitar módulos del kernel ===="
sudo modprobe overlay
sudo modprobe br_netfilter

echo "==== Fase 3: Configurar parámetros del sistema ===="
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF
sudo sysctl --system

echo "==== Fase 4: Instalar dependencias ===="
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg

echo "==== Fase 5: Instalar y configurar containerd ===="
sudo apt-get install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd


echo "==== Fase 6: Configurar repositorio de Kubernetes ===="
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.32/deb/Release.key \
  | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

sudo rm /etc/apt/sources.list.d/kubernetes.list
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.32/deb/ /" | sudo tee /etc/apt/sources.list.d/kubernetes.list

echo "==== Fase 7: Instalar kubelet, kubeadm y kubectl ===="
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl

echo "==== Fase 8: Inicializar el clúster ===="
sudo kubeadm init --apiserver-advertise-address=10.10.0.1 --pod-network-cidr=10.244.0.0/16

echo "==== Fase 9: Configurar acceso kubectl ===="
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config





echo "==== Fase 10: Instalar red Calico ===="
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.30.0/manifests/calico.yaml

echo "==== Fase 11: Obtener fingerprint del CA ===="
openssl x509 -pubkey -in /etc/kubernetes/pki/ca.crt | \
openssl rsa -pubin -outform der 2>/dev/null | \
sha256sum | awk '{print $1}'

echo "==== Instalación completada con éxito ===="
