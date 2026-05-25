FROM registry.access.redhat.com/ubi9/ubi:latest

RUN dnf install -y openssh-server openssh-clients procps-ng iproute net-tools && \
    dnf clean all

# Set up SSH
RUN ssh-keygen -A && \
    mkdir -p /run/sshd && \
    echo 'root:eval-studio' | chpasswd && \
    sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
