<div align="center">
    <h1>AutoNet</h1>
    <p>
        AutoNet validates and generates Containerlab network topologies and Ansible group variables using YAML and CSV input files
    </p>
</div>

<div align="center">


</div>

<div align="center" style="text-align: center;">

[![Topology Validation](https://github.com/underp01nt/AutoNet/actions/workflows/topologies.yml/badge.svg)](https://github.com/underp01nt/AutoNet/actions/workflows/topologies.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>


## Features
* Validate network topology prior to config generation
* Generate Containerlab (`.clab.yml`) topology files + Ansible `group_vars` inventories
* Produce FRRouting daemon configuration files
* Create Layer-2 switch startup configurations
* Support optional routing protocol configurations (like OSPF or BGP) via YAML

---

## Example Topologies

<table border="1">
  <tr>
    <td>
        <a href=https://github.com/underp01nt/AutoNet/tree/main/topologies/multi-site-enterprise> 
            Multi-Site Enterprise Network 
        </a>
    </td>
  </tr>
  <tr>
    <td>
        <a href=https://github.com/underp01nt/AutoNet/tree/main/topologies/ospf>
            OSPF Network 
        </a>
    </td>
  </tr>
  <tr>
    <td>
        <a href=https://github.com/underp01nt/AutoNet/tree/main/topologies/switches> 
            Layer-2 Switching 
        </a>
    </td>
  </tr>
  <tr>
    <td>
        <a href=https://github.com/underp01nt/AutoNet/tree/main/topologies/simple> 
            Simple LAN 
        </a>
    </td>
  </tr>
</table>

---

# Example topology project structure

```
topology/
├── <input_directory>/
│   ├── nodes.csv
│   ├── interfaces.csv
│   ├── links.csv
│   ├── ospf.yml              # optional
│   ├── bgp.yml               # optional
│   └── routing_policy.yml    # optional
├── <*> configs/
├── <*> group_vars/
└── <*> <topology_name>.clab.yml 
```

* ```<input_directory>``` is a required preliminary folder. It should contain three CSV files 
(nodes.csv, interfaces.csv, links.csv) detailing network metadata.
For reference of what these CSV files should like, you can find examples in existing [topologies](https://github.com/underp01nt/AutoNet/tree/main/topologies).

* The remaining YAML files are optional and only provide protocol-specific configuration.

* The **<*>** files are artifacts produced by AutoNet to support automated network deployment.

---

# Generated Files

Depending on the topology, AutoNet generates:

* Containerlab topology (`*.clab.yml`)
* Ansible `group_vars`
* FRRouting daemon configuration files
* Switch startup configuration files

---

# Building a Topology

1. Run the `utils/builder.py` script to generate required configuration artifacts 
```bash
python -m utils.builder <inputs_directory> \
    --name <topology_name> \
    --group <group_name> \
    --switch arista_ceos \
    --validate
```

| Argument             | Description                                          |
| -------------------- | ---------------------------------------------------- |
| `<inputs_directory>` | Directory containing the input CSV/YAML files        |
| `--name`             | Name of the Containerlab topology to generate        |
| `--group`            | Name of Ansible group                                |
| `--switch`           | Switch implementation (`arista_ceos` or `sr_linux`)  |
| `--validate`         | Perform topology validation before generating output |


2. Create an automation script to utilize data from the produced file in the ```group_vars``` folder. 
    * If you are using Ansible, you may use the [playbook template](https://github.com/underp01nt/AutoNet/blob/main/templates/configuration.yml)

---

# Deploying a Topology (with Ansible)

Navigate to the directory containing the generated .clab.yml file and start the lab:
```bash
sudo containerlab deploy -t <topology_name>.clab.yml
```

If using Ansible, run your playbook to configure the network nodes
```bash
ansible-playbook -i <inventory> <playbook>
```

To destroy the topology and clean up resources:

```bash
sudo containerlab destroy -t <topology_name>.clab.yml
```

> **Note:** Containerlab and the required container images (for example, FRRouting and Arista cEOS) must already be installed on the host system before deploying a topology.

---

# Topology Validation

When the `--validate` option is passed, AutoNet performs a number of consistency checks before generating any artifacts.

Examples include:
* Invalid IP addresses or CIDR notation
* Missing devices or interfaces referenced by links
* Subnet mismatches between routed links
* Duplicate interface endpoints
* Duplicate IP addresses
* Missing BGP configuration for BGP-enabled routers

Any failures are reported after validation.

# Supported node images

* FRRouting
* Arista cEOS
* Nokia SR Linux
* Linux hosts (e.g. Alpine Linux)
