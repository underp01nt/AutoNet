#!/bin/sh

# for troubleshooting
iptables -A INPUT -p icmp -j ACCEPT
iptables -A FORWARD -p icmp -j ACCEPT

# drop all inbound and forwarded traffic unless permitted
iptables -P INPUT DROP
iptables -P FORWARD DROP

# allow all outbound traffic
iptables -P OUTPUT ACCEPT

# allow loopback traffic
iptables -A INPUT -i lo -j ACCEPT

# allow ospf adjacency and BGP sessions
iptables -A INPUT -p ospf -j ACCEPT
iptables -A INPUT -p tcp --dport 179 -j ACCEPT

# allow Corporate users to access the Services network
iptables -A FORWARD -s 10.100.10.0/24 -d 10.100.2.0/24 -j ACCEPT
iptables -A FORWARD -s 10.100.10.0/24 -d 10.100.3.0/24 -j ACCEPT
iptables -A FORWARD -s 10.100.20.0/24 -d 10.100.2.0/24 -j ACCEPT
iptables -A FORWARD -s 10.100.20.0/24 -d 10.100.3.0/24 -j ACCEPT

# disallow traffic between neighbor LANs
iptables -A FORWARD -s 10.100.10.0/24 -d 10.100.20.0/24 -j DROP
iptables -A FORWARD -s 10.100.20.0/24 -d 10.100.10.0/24 -j DROP