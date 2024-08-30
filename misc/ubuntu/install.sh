#! /bin/bash

# Do not interract with me, please.
export DEBIAN_FRONTEND=noninteractive

# Install system dependencies
apt update
apt install -y make git curl ca-certificates software-properties-common

# add deadsnake repository for recent python versions
add-apt-repository -y ppa:deadsnakes/ppa

# add docker repository
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
     -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt update
apt install -y python3.12 python3-pip python3-poetry \
               docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Install NodeJS
curl -fsSL https://deb.nodesource.com/setup_20.x -o nodesource_setup.sh
bash nodesource_setup.sh
apt-get install -y nodejs
node -v

# Install and enable PNPM using corepack
corepack enable pnpm
corepack install -g pnpm
