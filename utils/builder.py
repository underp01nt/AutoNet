r"""
    Builds Containerlab topology and configuration files for network deployments.
    
    Options:
        **[REQUIRED]**
            `inputs`: "inputs" folder containing at least: [nodes.csv, links.csv, interfaces.csv]
            
        **[OPTIONAL]**
            `--name`: topology name
            `--group`: Ansible group name for group_vars
            `--switch`: Docker container kind for switch OS  (nokia_srlinux, arista_ceos)

    Program output:
        - *.clab.yml: Containerlab deployment file
        - configs/*: directory containing configuration files for one or more network node
        - group_vars/{--group}: Ansible group_vars file

    Example program call:
    ```
    python builder.py --name "example-lab" <inputs_directory_path> --group "nodes" --switch "arista_ceos"
    ```

    NOTES:
        1. All program output files and directories are placed in the parent of the `inputs` folder
        2. Switch interface convention::

            - arista_ceos: eth<port>
            - nokia_srlinux: ethernet-<slot>/<port>
"""

from ipaddress import ip_interface
from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq
from typing import Literal, Optional

import argparse
import csv
import json
import os

# minimum fields to qualify for YML builds
EXPECTED_NODES_CSV_FIELDS = ["name", "type"]
EXPECTED_INTERFACES_CSV_FIELDS = ["name", "interface", "ip_address", "roles"]
EXPECTED_LINKS_CSV_FIELDS = ["device_a", "interface_a", "device_b", "interface_b"]

# router images
DEFAULT_ROUTER_IMAGE = "frrouting/frr:latest"

# host images
DEFAULT_HOST_IMAGE = "alpine:latest"

# switch images
DEFAULT_SRLINUX_IMAGE = "ghcr.io/nokia/srlinux" 
DEFAULT_CEOS_IMAGE = "ceos:4.36.1F"

# for parsing protocols field in nodes.csv to daemon names
PROTOCOLS_TO_DAEMONS = {"bgp": "bgpd", "ospf": "ospfd", "isis": "isisd","rip": "ripd"}

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)

def _validate_fieldnames(fields: set, mode: Literal["nodes", "links", "interfaces"]) -> bool:
    match mode:
        case "nodes": return set(EXPECTED_NODES_CSV_FIELDS).issubset(fields)
        case "links": return set(EXPECTED_LINKS_CSV_FIELDS).issubset(fields)
        case "interfaces": return set(EXPECTED_INTERFACES_CSV_FIELDS).issubset(fields)

class NetworkTopology:
    r"""
    Stores node-related data for generating configs and .clab.yml artifacts
    """
    def __init__(self, name: str, group: str, inputs_dir: str, switch_kind="arista_ceos", **filepaths):
        self.name = name if name else "my-network"        # assigns containerlab name
        self.devices: dict = {}                           # stores group_vars file data

        # defines nodes and links data for .clab.yml
        self.nodes: dict = {}
        self.links: list[dict] = []  # list of "endpoints" dict (e.g. [{endpoints: ["pc1:eth2, r1:eth1"]}, ...])

        # defines node-type mapping (e.g. r1: router)
        self.node_type: dict[str, str] = {}
        # maps switch name to its interfaces in-use
        self.switch_interfaces: dict[str, set] = {}
        # option to use SR Linux or cEOS
        self.switch_kind = switch_kind

        # global configurations
        self.globals: Optional[dict] = None

        # I/O related attributes
        self.main_dir = Path(inputs_dir).parent
        self.output_clab_file = self.main_dir / f"{name or "topology"}.clab.yml"

        (self.main_dir / f"group_vars").mkdir(parents=True, exist_ok=True)
        self.output_group_vars_file = self.main_dir / f"group_vars" / f"{group or "group"}.yml"
        
        self.nodes_file_path: Path = filepaths["nodes_file_path"]              # REQUIRED FILE
        self.links_file_path: Path  = filepaths["links_file_path"]             # REQUIRED FILE
        self.interfaces_file_path: Path = filepaths["interfaces_file_path"]    # REQUIRED FILE
        self.bgp_file_path = filepaths.get("bgp_file_path", None)              # OPTIONAL FILE
        self.policy_file_path = filepaths.get("policy_file_path", None)        # OPTIONAL FILE

        # parse each input csv file      
        self.parse_interfaces_csv()                      # builds self.devices
        self.parse_nodes_csv()                           # builds self.nodes
        self.parse_links_csv()                           # builds self.links
        
        # parse optional yml files
        if self.bgp_file_path and os.path.exists(self.bgp_file_path): self.parse_bgp_file()
        if self.policy_file_path and os.path.exists(self.policy_file_path): self.parse_bgp_file()

        # validate the newly created topology to detect any network inconsistencies
        # self.validate_topology()

        if self.switch_interfaces:
            for switch in self.switch_interfaces:
                match self.switch_kind:
                    case "arista_ceos": self.create_ceos_switch_cli_file(switch)
                    case "nokia_srlinux": self.create_srlinux_switch_cli_file(switch)
                    case _: raise ValueError("Unrecognized switch image")

    def _get_switch_image(self) -> str:
        r"""
        Returns switch image given the selected switch kind 
        """
        match self.switch_kind:
            case "arista_ceos": return DEFAULT_CEOS_IMAGE
            case "sr_linux": return DEFAULT_SRLINUX_IMAGE
            case _: raise ValueError("Unknown switch kind")

    def write_all(self):
        self.to_clab_yml()
        self.to_group_vars_file()

    def to_clab_yml(self): 
        with open(self.output_clab_file, "w") as file:
            data = {"name": self.name, "topology": {"nodes": self.nodes, "links": self.links}}
            yaml.dump(data, file)

    # TODO: subnets should be registered, check subnets, subnet prefix lengths, and node interfaces
    def validate_topology(self):
        raise NotImplementedError()

    def to_group_vars_file(self):
        with open(self.output_group_vars_file, "w") as file:
            data = {"devices": self.devices}
            if self.globals: data["globals"] = self.globals
            yaml.dump(data, file)

    def create_ceos_switch_cli_file(self, name: str) -> str:
        r"""
            Creates a .cli file for a cEOS switch, returns path of the .cli file
        """
        switch_dir = self.main_dir / "configs" / name
        switch_dir.mkdir(parents=True, exist_ok=True)

        with open(switch_dir / f"{name}.cli", "w") as ceos_switch_config:
            ceos_switch_config.write(f"hostname {name}\n")
            ceos_switch_config.write(f"conf t\n\n")

            for interface in self.switch_interfaces[name]:
                ceos_switch_config.write(f"interface {interface}\n")
                ceos_switch_config.write("  no shut\n")
                ceos_switch_config.write("  switchport\n")
                ceos_switch_config.write("!\n")

        return f"configs/{name}/{name}.cli"

    def create_srlinux_switch_cli_file(self, name: str) -> str:
        r"""
            Creates a .cli file for an SR-Linux switch, returns path of the .cli file
        """

        switch_dir = self.main_dir / "configs" / name
        switch_dir.mkdir(parents=True, exist_ok=True)

        # configuration for treating an sr-linux device as a switch
        with open(switch_dir / f"{name}.cli", "w") as srlinux_switch_config:
            srlinux_switch_config.write("enter candidate \n")
            srlinux_switch_config.write(f"edit system name host-name {name}")
            srlinux_switch_config.write("set network-instance mac-vrf-1 type mac-vrf \n")
            srlinux_switch_config.write("set network-instance mac-vrf-1 admin-state enable \n\n")
            
            for interface in self.switch_interfaces[name]:
                # create interface
                srlinux_switch_config.write(f"set interface {interface} admin-state enable \n")
                # define interface type
                srlinux_switch_config.write(f"set interface {interface} subinterface 0 type bridged \n\n")
                # assign interface to switch instance
                srlinux_switch_config.write(f"set network-instance mac-vrf-1 interface {interface}.0 \n")

            srlinux_switch_config.write("commit now")

        return f"configs/{name}/{name}.cli"
    
    def translate_bgp_neighbors(self, router: str, neighbors: list[str]) -> list[dict]:
        r"""
            Translates neighbor hostnames to AS-aware peer IP addresses and AS numbers for BGP adjacency

            :router: name of router
            :neighbors: list of neighbors specified by user for this router
        """ 
        peers = set()

        for neighbor in neighbors:  
            # iBGP, just get peer's loopback address  (only when theres IGP underlay to advertise loopbacks)
            # if self.devices[router]["asn"] == self.devices[neighbor]["asn"]:
            #     peers.add(
            #         (
            #             ip_interface(self.devices[neighbor]["interfaces"]["lo"]["ip_address"]).ip,
            #             self.devices[neighbor]["asn"]
            #         )
            #     )
            # else: 

            # eBGP
            for link in self.links: 
                a, b = link["endpoints"]

                node_a, intf_a = a.split(":")
                node_b, intf_b = b.split(":")

                if self.devices[node_a].get("bgp") and self.devices[node_b].get("bgp"):
                    ip_address, remote_as = None, None  

                    if node_a == router and node_b == neighbor:
                        ip_address = ip_interface(self.devices[node_b]["interfaces"][intf_b]["ip_address"]).ip
                        remote_as = self.devices[neighbor]["bgp"]["asn"]
 
                    elif node_b == router and node_a == neighbor:
                        ip_address = ip_interface(self.devices[node_a]["interfaces"][intf_a]["ip_address"]).ip
                        remote_as = self.devices[node_a]["bgp"]["asn"] 
                    
                    if ip_address and remote_as:
                        peers.add((ip_address, remote_as))

        return [{"ip_address": str(ip), "remote_as": remote_as} for ip, remote_as in peers]
    
    def parse_bgp_file(self):
        if not self.bgp_file_path: return
        else:
            with open(self.bgp_file_path, "r") as file:
                data = yaml.load(file)
                bgp_routers = data["bgp"]["routers"]

                if data["bgp"].get("globals"):
                    self.globals = data["bgp"]["globals"]

                for router, config in bgp_routers.items():
                    self.devices[router]["bgp"] = {"asn": config["asn"]}

                    if config.get("networks"): 
                        self.devices[router]["bgp"]["networks"] = config["networks"]
                    if config.get("neighbors"):
                        self.devices[router]["bgp"]["neighbors"] = config["neighbors"]

                # all bgp metadata retrieved, resolve neighbor identity to relevant metadata
                for router, config in self.devices.items():
                    if "bgp" not in config:
                        continue

                    neighbors = config["bgp"]["neighbors"]
                    config["bgp"]["neighbors"] = self.translate_bgp_neighbors(router, neighbors)

    def parse_policy_file(self):
        if not self.policy_file_path: return
        else:
            with open(self.policy_file_path, "r") as file:
                routing_policy = yaml.load(file)["routing_policy"]
                redistribute = routing_policy.get("redistribute", {})

                for router, protocols in redistribute.items():
                    if "ospf" in protocols:
                        self.devices[router]["ospf"]["redistribute"] = protocols["ospf"]

                    if "bgp" in protocols:
                        self.devices[router]["bgp"]["redistribute"] = protocols["bgp"]

    def parse_interfaces_csv(self):
        with open(self.interfaces_file_path, "r") as interfaces_file:
            reader = csv.DictReader(interfaces_file)
            fields = reader.fieldnames or []
            
            if _validate_fieldnames(set(fields), "interfaces"):
                for row in reader:
                    # define device role/s
                    match row["roles"]:
                        case "router": roles = CommentedSeq(["router"])
                        case "host": roles = CommentedSeq(["host"])
                        case _: roles = CommentedSeq(["Unknown"])
                    roles.fa.set_flow_style()

                    current_device = self.devices.setdefault(row["name"], {"roles": roles})
                    interfaces = current_device.setdefault("interfaces", {})
                    current_interface = interfaces.setdefault(row["interface"], {})

                    # assign IP address
                    current_interface["ip_address"] = row["ip_address"]
                    # assign OSPF area
                    if row["ospf_area"]: current_interface["ospf_area"] = int(row["ospf_area"])
                    # assign passive interface (if applicable)
                    if row["ospf_passive"]: 
                        current_interface["ospf_passive"] = (row["ospf_passive"] == "true")

            else: raise ValueError("Interfaces header fields are inconsistent")

    def parse_links_csv(self):
        with open(self.links_file_path, mode="r", newline="") as links_file:
            reader = csv.DictReader(links_file)
            fields = reader.fieldnames or []
            
            if _validate_fieldnames(set(fields), "links"):
                links = []
                for row in reader:
                    endpt_A = f"{row['device_a']}:{row['interface_a']}"
                    endpt_B = f"{row['device_b']}:{row['interface_b']}"
                    
                    endpoints = CommentedSeq([endpt_A, endpt_B])
                    endpoints.fa.set_flow_style()
                    
                    links.append({"endpoints": endpoints})

                    for device, interface in [
                        (row["device_a"], row["interface_a"]), 
                        (row["device_b"], row["interface_b"])
                    ]:
                        if self.node_type[device] == "switch":   
                            # {'sw1': {'e1-2', 'e1-1',... }}
                            self.switch_interfaces.setdefault(device, set()).add(interface)

                self.links = links
            else: 
                raise ValueError("Links header fields are inconsistent")
    
    def create_daemons_file(self, device_name, protocols: list[str]):
        r"""
            Creates a daemons file for a device
            
            :protocols: list of routing protocol/s used by this device (example: ["ospf", bgp"]
        """
        
        with open("templates/daemons.json") as f: 
            daemons = json.load(f)
            for protocol in protocols:
                daemon = PROTOCOLS_TO_DAEMONS.get(protocol)

                if daemon: daemons[daemon] = "yes"
                else: raise ValueError(f"Invalid protocol name: {protocol}")

        device_dir = self.main_dir / "configs" / device_name
        device_dir.mkdir(parents=True, exist_ok=True) 

        with open(device_dir / f"daemons", "w") as f:
            for daemon, enabled in daemons.items():
                f.write(f"{daemon}={enabled}\n")

    def parse_nodes_csv(self):
        with open(self.nodes_file_path, mode="r", newline="") as nodes_file:
            reader = csv.DictReader(nodes_file)
            fields = reader.fieldnames or []
            
            if _validate_fieldnames(set(fields), "nodes"):    
                for row in reader: 
                    if row.get("next_hop"):  
                        self.devices[row["name"]]["next_hop"] = row["next_hop"]

                    kind = "linux"
                    match row["type"]:
                        case "router": 
                            if not row["protocols"]:
                                self.nodes[row["name"]] = {
                                    "kind": kind, 
                                    "image": DEFAULT_ROUTER_IMAGE
                                }
                            else:
                                # parse protocols field
                                parsed_protocols = [p for p in row["protocols"].split(";") if p.strip()]
                                self.devices[row["name"]]["protocols"] = parsed_protocols
                                
                                # create daemon file for this (router) node
                                self.create_daemons_file(row["name"], parsed_protocols)
                                
                                self.nodes[row["name"]] = {
                                    "kind": kind, 
                                    "image": DEFAULT_ROUTER_IMAGE,
                                    "binds": [
                                        f"configs/{row["name"]}/daemons:/etc/frr/daemons"
                                    ],
                                    "exec": ["touch /etc/frr/vtysh.conf"]
                                }
                            self.node_type[row["name"]] = "router"

                        case "host": self.nodes[row["name"]] = {
                                "kind": kind, 
                                "image": DEFAULT_HOST_IMAGE,
                            }; self.node_type[row["name"]] = "host"

                        case "switch":
                            self.nodes[row["name"]] = {
                                "kind": self.switch_kind,
                                "image": self._get_switch_image(),
                                "startup-config": f"configs/{row["name"]}/{row["name"]}.cli"
                            }; self.node_type[row["name"]] = "switch"

                            roles = CommentedSeq(["switch"])
                            roles.fa.set_flow_style()
                            self.devices[row["name"]] = {"roles": roles}
            else:
                raise ValueError("Nodes header fields are inconsistent")  

if __name__ == "__main__": 
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", type=str)     # inputs folder
    parser.add_argument("--name")               # topology name
    parser.add_argument("--group")              # group name for Ansible
    parser.add_argument("--switch", type=str)   # switch option
    args = parser.parse_args()

    nodes_file_path = os.path.join(args.inputs, "nodes.csv")
    links_file_path = os.path.join(args.inputs, "links.csv")
    interfaces_file_path = os.path.join(args.inputs, "interfaces.csv")
    
    bgp_file_path = os.path.join(args.inputs, "bgp.yml")
    policy_file_path = os.path.join(args.inputs, "routing_policy.yml")

    no_nodes = not os.path.exists(nodes_file_path)
    no_links = not os.path.exists(links_file_path)
    no_interfaces = not os.path.exists(interfaces_file_path)

    if no_nodes: print("nodes.csv not detected")
    if no_links: print("links.csv not detected")
    if no_interfaces: print("interfaces.csv not detected")
    
    if not (no_nodes or no_links or no_interfaces):
        topology = NetworkTopology(args.name, args.group, args.inputs, 
                                   switch_kind=args.switch,
                                   nodes_file_path=nodes_file_path,
                                   links_file_path=links_file_path,
                                   interfaces_file_path=interfaces_file_path,
                                   bgp_file_path=bgp_file_path,
                                   policy_file_path=policy_file_path,
                                   )
                                   
        topology.write_all()
        print("*** Successfully defined topology ***\n")