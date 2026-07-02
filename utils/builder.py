"""
    Builds Containerlab topology-related files.
    
    Options:

        inputs: inputs folder containing [nodes.csv, links.csv, interfaces.csv]
        --name: topology name
        --group: Ansible group name for group_vars
"""

from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq
from typing import Literal
import argparse, csv, json, os

# minimum fields to qualify for YML builds
EXPECTED_NODES_CSV_FIELDS = ["name", "type"]
EXPECTED_INTERFACES_CSV_FIELDS = ["name", "interface", "ip_address", "roles"]
EXPECTED_LINKS_CSV_FIELDS = ["device_a", "interface_a", "device_b", "interface_b"]

DEFAULT_ROUTER_IMAGE = "frrouting/frr:latest"
DEFAULT_HOST_IMAGE = "alpine:latest"
DEFAULT_SWITCH_IMAGE = "ghcr.io/nokia/srlinux"   # sr_linux

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
    def __init__(self, name: str, group: str, inputs_dir: str):
        self.name = name if name else "my-network"  # assigns containerlab name
        self.nodes: dict = {}
        self.links: list[dict] = []

        # defines node-type mapping (e.g. r1: router)
        self.node_type: dict[str, str] = {}
        # maps switch name to its interfaces
        self.switch_interfaces: dict[str, set] = {}

        # I/O related attributes
        self.main_dir = Path(inputs_dir).parent
        self.output_clab_file = self.main_dir / f"{name}.clab.yml"

        (self.main_dir / f"group_vars").mkdir(parents=True, exist_ok=True)
        self.output_group_vars_file = self.main_dir / f"group_vars" / f"{group}.yml"
        
        self.nodes_file_path: Path = Path(inputs_dir) / f"nodes.csv" 
        self.links_file_path: Path  = Path(inputs_dir) / f"links.csv" 
        self.interfaces_file_path: Path = Path(inputs_dir) / f"interfaces.csv" 

        if os.path.exists(nodes_file_path): self.parse_nodes_csv()
        if os.path.exists(links_file_path): self.parse_links_csv()

        if self.switch_interfaces:
            for switch in self.switch_interfaces:
                self.create_switch_cli_file(switch)

    def to_clab_yml(self): 
        with open(self.output_clab_file, "w") as file:
            data = {"name": self.name, "topology": {"nodes": self.nodes, "links": self.links}}
            yaml.dump(data, file)

    def to_group_vars_file(self):
        if os.path.exists(self.interfaces_file_path): 
            with open(self.interfaces_file_path, mode="r", newline="") as interfaces_file:
                reader = csv.DictReader(interfaces_file)
                fields = reader.fieldnames or []
                
                if _validate_fieldnames(set(fields), "interfaces"):
                    group_vars_data = {"devices": {}}
                    
                    for row in reader:
                        # define device role/s
                        match row["roles"]:
                            case "router": roles = CommentedSeq(["router"])
                            case "host": roles = CommentedSeq(["host"])
                            case _: roles = CommentedSeq(["Unknown"])
                        roles.fa.set_flow_style()

                        current_device = group_vars_data["devices"].setdefault(
                            row["name"], 
                            {"roles": roles}
                        )

                        if row.get("default_gateway"):  # assign default gateway for hosts
                            current_device["default_gateway"] = row["default_gateway"]

                        interfaces = current_device.setdefault("interfaces", {})
                        current_interface = interfaces.setdefault(row["interface"], {})

                        # assign IP address
                        current_interface["ip_address"] = row["ip_address"]
                        # assign OSPF area
                        if row["ospf_area"]: current_interface["ospf_area"] = int(row["ospf_area"])
                        
                    with open(self.output_group_vars_file, "w") as f:
                        yaml.dump(group_vars_data, f)
        else:
            print("interfaces.csv not detected")

    def create_switch_cli_file(self, name: str) -> str:
        r"""
            Creates a .cli file for a switch, returns path of the .cli file
        """

        switch_dir = self.main_dir / "configs" / name
        switch_dir.mkdir(parents=True, exist_ok=True)

        # configuration for treating an sr-linux device as a switch
        with open(switch_dir / f"{name}.cli", "w") as switch_config:
            switch_config.write("enter candidate \n")
            switch_config.write("set network-instance mac-vrf-1 type mac-vrf \n")
            switch_config.write("set network-instance mac-vrf-1 admin-state enable \n\n")
            
            for interface in self.switch_interfaces[name]:
                # create interface
                switch_config.write(f"set interface {interface} admin-state enable \n")
                # define interface type
                switch_config.write(f"set interface {interface} subinterface 0 type bridged \n\n")
                # assign interface to switch instance
                switch_config.write(f"set network-instance mac-vrf-1 interface {interface}.0 \n")

            switch_config.write("commit now")

        return f"configs/{name}/{name}.cli"

    def parse_links_csv(self):
        try:
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
                    raise ValueError("Input header fields are inconsistent")
        except Exception as e: print(e)
    
    def create_daemons_file(self, device_name, protocols: str):
        """
            Creates a daemons file for a device\n
            :protocols: string of routing protocol/s (example: "ospf;bgp", "bgp; ospf", "bgp")
        """
        parsed_protocols = [p for p in protocols.split(";") if p.strip()]
        
        with open("templates/daemons.json") as f: 
            daemons = json.load(f)
            for parsed_protocol in parsed_protocols:
                daemon = PROTOCOLS_TO_DAEMONS.get(parsed_protocol)

                if daemon: daemons[daemon] = "yes"
                else: raise ValueError(f"Invalid protocol name: {parsed_protocol}")

        device_dir = self.main_dir / "configs" / device_name
        device_dir.mkdir(parents=True, exist_ok=True) 

        with open(device_dir / f"daemons", "w") as f:
            for daemon, enabled in daemons.items():
                f.write(f"{daemon}={enabled}\n")

    def parse_nodes_csv(self):
        try:
            with open(self.nodes_file_path, mode="r", newline="") as nodes_file:
                reader = csv.DictReader(nodes_file)
                fields = reader.fieldnames or []
                
                if _validate_fieldnames(set(fields), "nodes"):            
                    for row in reader: 
                        kind = "linux"
                        match row["type"]:
                            case "router": 
                                if not row["protocols"]:
                                    self.nodes[row["name"]] = {
                                        "kind": kind, 
                                        "image": DEFAULT_ROUTER_IMAGE
                                    }
                                else:
                                    # create daemon file for this (router) node
                                    self.create_daemons_file(row["name"], row["protocols"])
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
                                    "kind": "nokia_srlinux",
                                    "image": DEFAULT_SWITCH_IMAGE,
                                    "startup-config": f"configs/{row["name"]}/{row["name"]}.cli"
                                }; self.node_type[row["name"]] = "switch"
                else:
                    raise ValueError("Input header fields are inconsistent")  
        except Exception as e: print(e)

if __name__ == "__main__": 
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", type=str)   # inputs folder
    parser.add_argument("--name")             # topology name
    parser.add_argument("--group")            # group name for Ansible
    args = parser.parse_args()

    nodes_file_path = os.path.join(args.inputs, "nodes.csv")
    links_file_path = os.path.join(args.inputs, "links.csv")
    interfaces_file_path = os.path.join(args.inputs, "interfaces.csv")

    if not args.name:
        raise ValueError("Please provide a topology name")
    
    topology = NetworkTopology(args.name, args.group, args.inputs)
    topology.to_group_vars_file()
    
    if not topology.links: print("links.csv not detected")
    elif not topology.nodes: print("nodes.csv not detected")
    else:
        topology.to_clab_yml()
        print("*** Successfully defined topology ***\n")