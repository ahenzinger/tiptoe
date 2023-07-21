# SET
bwlimit=100mbit
delay=50ms # RTT

if test -z "$(lsmod | grep ifb)"; then
        sudo modprobe ifb
fi

# Shapes ingress traffic
sudo ip link set dev ifb0 up
sudo tc qdisc add dev ifb0 root handle 1: htb r2q 1
sudo tc class add dev ifb0 parent 1: classid 1:1 htb rate 100mbit
sudo tc filter add dev ifb0 parent 1: matchall flowid 1:1

sudo tc qdisc add dev ens5 ingress
sudo tc filter add dev ens5 ingress matchall action mirred egress redirect dev ifb0

# Shapes egress traffic
sudo tc qdisc del dev ens5 root
sudo tc qdisc add dev ens5 root netem rate 100mbit delay 50ms

echo rate $bwlimit delay $delay
