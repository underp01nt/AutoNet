## Network Architecture Diagram

<div align="center">

![Alt text](multi.svg)

*Figure 1. Enterprise network topology*

</div>

 * **AS10000** represents the ISP provider network
 * **AS10001** represents the Corporate network (Access router and client LANs)
 * **AS10002** represents the Services network hosting the (web) application servers and the database

## Network Configuration

<div align="center">

<h2>Subnet Design </h2>

| Subnet Name       | Network Address (/n) | Usable Hosts | First Valid Host | Last Valid Host |    AS    |
| :-------------:   | :------------------: | :----------: | :--------------: | :-------------: | :------: |
| Access ↔ Core-A   | 10.100.1.0/30        | 2            | 10.100.1.1       | 10.100.1.2      |   10001  |
| Access ↔ Core-B   | 10.100.1.4/30        | 2            | 10.100.1.5       | 10.100.1.6      |   10001  |
| Core-A ↔ Core-B   | 10.100.1.8/30        | 2            | 10.100.1.9       | 10.100.1.10     |   10001  |
| Subnet A          | 10.100.10.0/24       | 254          | 10.100.10.1      | 10.100.10.254   |   10001  |
| Subnet B          | 10.100.20.0/24       | 254          | 10.100.20.1      | 10.100.20.254   |   10001  |
| PE1 ↔ Access      | 10.100.0.0/30        | 2            | 10.100.0.1       | 10.100.0.2      | Inter-AS |
| PE2 ↔ Access      | 10.100.0.4/30        | 2            | 10.100.0.5       | 10.100.0.6      | Inter-AS | 
| PE1 ↔ PE2         | 10.100.0.8/30        | 2            | 10.100.0.9       | 10.100.0.10     |   10000  |
| PE1 ↔ Services    | 10.100.0.12/30       | 2            | 10.100.0.13      | 10.100.0.14     | Inter-AS | 
| PE2 ↔ Services    | 10.100.0.16/30       | 2            | 10.100.0.17      | 10.100.0.18     | Inter-AS |
| Access Loopback   | 10.100.255.1/32      | 1            | 10.100.255.1     | 10.100.255.1    |   10001  |
| Core-A Loopback   | 10.100.255.2/32      | 1            | 10.100.255.2     | 10.100.255.2    |   10001  |
| Core-B Loopback   | 10.100.255.3/32      | 1            | 10.100.255.3     | 10.100.255.3    |   10001  |
| PE1 Loopback      | 10.100.255.4/32      | 1            | 10.100.255.4     | 10.100.255.4    |   10000  |
| PE2 Loopback      | 10.100.255.5/32      | 1            | 10.100.255.5     | 10.100.255.5    |   10000  |
| Services Loopback | 10.100.255.6/32      | 1            | 10.100.255.6     | 10.100.255.6    |   10002  |
| Servers           | 10.100.2.0/24        | 254          | 10.100.2.1       | 10.100.2.254    |   10002  |

<h2>Links</h2>

| Link              | Interface A   | Interface B     |
| ----------------- | ------------- | --------------- |
| Access ↔ Core-A   | Access `eth2` | Core-A   `eth1` |
| Access ↔ Core-B   | Access `eth3` | Core-B   `eth1` |
| Core-A ↔ Core-B   | Core-A `eth2` | Core-B   `eth2` |
| Core-A ↔ Subnet A | Core-A `eth3` | Host-A   `eth1` |
| Core-B ↔ Subnet B | Core-B `eth3` | Host-B   `eth1` |
|    PE1 ↔ Access   | PE1    `eth1` | Access   `eth1` |
|    PE2 ↔ Access   | PE2    `eth1` | Access   `eth4` |
|    PE1 ↔ PE2      | PE1    `eth2` | PE2      `eth2` |
|    PE1 ↔ Services | PE1    `eth3` | Services `eth1` |
|    PE2 ↔ Services | PE2    `eth3` | Services `eth2` |


<h2>Interface Addressing</h2>

<b>AS 10001</b>
| Device   | Interface | IP Address   |      Subnet Mask      |  OSPF Area  | 
| :------: | :-------: | :----------- | :-------------------: | :---------: |
| Access   | eth2      | 10.100.1.1   | 255.255.255.252 (/30) |      0      | 
| Access   | eth3      | 10.100.1.5   | 255.255.255.252 (/30) |      0      | 
| Access   | lo        | 10.100.255.1 | 255.255.255.255 (/32) |      0      | 
| Core-A   | eth1      | 10.100.1.2   | 255.255.255.252 (/30) |      0      |
| Core-A   | eth2      | 10.100.1.9   | 255.255.255.252 (/30) |      0      | 
| Core-A   | eth3      | 10.100.10.1  | 255.255.255.0 (/24)   | 0 / PASSIVE | 
| Core-A   | lo        | 10.100.255.2 | 255.255.255.255 (/32) |      0      | 
| Core-B   | eth1      | 10.100.1.6   | 255.255.255.252 (/30) |      0      |
| Core-B   | eth2      | 10.100.1.10  | 255.255.255.252 (/30) |      0      |
| Core-B   | eth3      | 10.100.20.1  | 255.255.255.0 (/24)   | 0 / PASSIVE | 
| Core-B   | lo        | 10.100.255.3 | 255.255.255.255 (/32) |      0      |
| Host-A   | eth1      | 10.100.10.10 | 255.255.255.0 (/24)   |      /      |
| Host-B   | eth1      | 10.100.20.10 | 255.255.255.0 (/24)   |      /      |
| PE1      | eth1      | 10.100.0.1   | 255.255.255.252 (/30) |   NO OSPF   | 
| Access   | eth1      | 10.100.0.2   | 255.255.255.252 (/30) |   NO OSPF   | 
| PE2      | eth1      | 10.100.0.5   | 255.255.255.252 (/30) |   NO OSPF   |  
| Access   | eth4      | 10.100.0.6   | 255.255.255.252 (/30) |   NO OSPF   | 
| PE1      | eth2      | 10.100.0.9   | 255.255.255.252 (/30) |   NO OSPF   | 
| PE2      | eth2      | 10.100.0.10  | 255.255.255.252 (/30) |   NO OSPF   | 
| PE1      | eth3      | 10.100.0.13  | 255.255.255.252 (/30) |   NO OSPF   | 
| Services | eth1      | 10.100.0.14  | 255.255.255.252 (/30) |   NO OSPF   | 
| PE2      | eth3      | 10.100.0.17  | 255.255.255.252 (/30) |   NO OSPF   | 
| Services | eth2      | 10.100.0.18  | 255.255.255.252 (/30) |   NO OSPF   | 
| PE1      | lo        | 10.100.255.4 | 255.255.255.255 (/32) |   NO OSPF   | 
| PE2      | lo        | 10.100.255.5 | 255.255.255.255 (/32) |   NO OSPF   | 
| Services | lo        | 10.100.255.6 | 255.255.255.255 (/32) |      0      | 


<h2>Firewall Rules</h2>

| Firewall          | P/D | Source         | Destination    | Protocol / Port | Purpose |
|------------------ |-----|----------------|----------------|-----------------|---------|
| Access            | P   | coreA, coreB   | Access         | OSPF/89         | allow OSPF adjacencies |
| Access            | P   | PE1, PE2       | Access         | TCP/179         | allow BGP peering      |
| Access            | P   | 10.100.10.0/24 | 10.100.2.0/24  | Any             | allow Subnet A to access application servers |
| Access            | P   | 10.100.20.0/24 | 10.100.2.0/24  | Any             | Allow Subnet B to access the application servers |
| Access            | P   | 10.100.10.0/24 | 10.100.3.0/24  | Any             | Allow Subnet A to access DB |
| Access            | P   | 10.100.20.0/24 | 10.100.3.0/24  | Any             | Allow Subnet B to access DB |
| Access            | D   | 10.100.10.0/24 | 10.100.20.0/24 | Any             | prevent Subnet A and Subnet B communication | 
| Access            | D   | 10.100.20.0/24 | 10.100.10.0/24 | Any             | prevent Subnet A and Subnet B communication |
| Services          | P   | PE1, PE2       | Services       | TCP/179         | allow BGP peering |
| Services          | P   | 10.100.10.0/24 | 10.100.2.0/24  | TCP/80          | allow HTTP access to application servers |
| Services          | P   | 10.100.10.0/24 | 10.100.2.0/24  | TCP/443         | allow HTTPS access to application servers |
| Services          | P   | 10.100.20.0/24 | 10.100.2.0/24  | TCP/80          | allow HTTP access to application servers |
| Services          | P   | 10.100.20.0/24 | 10.100.2.0/24  | TCP/443         | allow HTTPS access to application servers |
| Services          | P   | 10.100.10.0/24 | 10.100.3.0/24  | TCP/5432        | allow Subnet A to access the PostgreSQL database |
| Services          | P   | 10.100.20.0/24 | 10.100.3.0/24  | TCP/5432        | allow Subnet B to access the PostgreSQL database |
| Services          | P   | 10.100.2.0/24  | 10.100.3.0/24  | TCP/5432        | allow application servers to access the PostgreSQL database |
| Access / Services | P   | Any            | Any            | ICMP            | allow pinging for troubleshooting |
| Access / Services | D   | Any            | Any            | Any             | all other unspecified traffic is blocked |

</div>
