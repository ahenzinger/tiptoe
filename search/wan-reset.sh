# Undo ingress shaping
sudo tc qdisc del dev ens5 ingress
sudo tc qdisc del dev ifb0 root

# Undo egress shaping
sudo tc qdisc del dev ens5 root
