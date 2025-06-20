#!/bin/bash

echo "==================================="
echo "   DESINSTALADOR DE KUBERNETES"
echo "==================================="
echo

# Detener y deshabilitar servicios de Kubernetes
echo "🔄 Deteniendo y deshabilitando servicios de Kubernetes..."
sudo systemctl stop kubelet
sudo systemctl disable kubelet
sudo rm -f /etc/sysctl.d/k8s.conf
sudo sysctl --system
echo "✅ Servicios de Kubernetes detenidos"
echo

# Eliminar componentes instalados
echo "🗑️  Eliminando componentes de Kubernetes instalados..."
sudo apt remove -y kubeadm kubectl kubelet kubernetes-cni kube* 
sudo apt autoremove -y
echo "✅ Componentes eliminados"
echo

# Borrar configuraciones y estado local
echo "🧹 Limpiando configuraciones y estado local..."
echo "   - Eliminando ~/.kube"
sudo rm -rf ~/.kube
sudo rm -rf /etc/kubernetes
sudo rm -rf /var/lib/etcd
sudo rm -rf /var/lib/kubelet
sudo rm -rf /etc/cni
sudo rm -rf /opt/cni
sudo rm -rf /var/lib/cni/
sudo rm -rf /var/run/kubernetes/
echo "✅ Configuraciones y estado local limpiados"
echo

# Eliminar reglas de red y bridges
echo "🌐 Eliminando interfaces de red y bridges..."
echo "   - Eliminando cni0"
sudo ip link delete cni0    2>/dev/null
sudo ip link delete flannel.1 2>/dev/null
#sudo ip link delete docker0   2>/dev/null
echo "✅ Interfaces de red eliminadas"
echo

# Limpiar entrada del repositorio de Kubernetes
echo "📦 Limpiando repositorio de Kubernetes..."
echo "   - Eliminando kubernetes.list"
sudo rm /etc/apt/sources.list.d/kubernetes.list
echo "   - Eliminando keyring de Kubernetes"
sudo rm /usr/share/keyrings/kubernetes-archive-keyring.gpg
echo "   - Actualizando repositorios"
sudo apt update
echo "✅ Repositorio de Kubernetes limpiado"
echo

echo "==================================="
echo "   ✅ DESINSTALACIÓN COMPLETADA"
echo "==================================="
