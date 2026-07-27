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

# permit BGP
iptables -A INPUT -p tcp --dport 179 -j ACCEPT

# allow Corporate users to access the web servers
iptables -A FORWARD -p tcp -s 10.100.10.0/24 -d 10.100.2.0/24 --dport 80 -j ACCEPT
iptables -A FORWARD -p tcp -s 10.100.10.0/24 -d 10.100.2.0/24 --dport 443 -j ACCEPT
iptables -A FORWARD -p tcp -s 10.100.20.0/24 -d 10.100.2.0/24 --dport 80 -j ACCEPT
iptables -A FORWARD -p tcp -s 10.100.20.0/24 -d 10.100.2.0/24 --dport 443 -j ACCEPT

# allow Corporate users to access the database
iptables -A FORWARD -p tcp -s 10.100.10.0/24 -d 10.100.3.0/24 --dport 5432 -j ACCEPT
iptables -A FORWARD -p tcp -s 10.100.20.0/24 -d 10.100.3.0/24 --dport 5432 -j ACCEPT

# allow application servers to access the database
iptables -A FORWARD -p tcp -s 10.100.2.0/24 -d 10.100.3.0/24 --dport 5432 -j ACCEPT