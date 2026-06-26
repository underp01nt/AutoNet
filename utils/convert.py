from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq
from typing import Literal
import os, csv, argparse

# minimum fields to qualify for YML builds
EXPECTED_NODES_CSV_FIELDS = ["name", "type"]
EXPECTED_INTERFACES_CSV_FIELDS = ["name", "interface", "ip_address", "roles"]
EXPECTED_LINKS_CSV_FIELDS = ["device_a", "interface_a", "device_b", "interface_b"]

DEFAULT_ROUTER_IMAGE = "frrouting/frr:latest"
DEFAULT_HOST_IMAGE = "alpine:latest"

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)

def _validate_fieldnames(fields: set, mode: Literal["nodes", "links", "interfaces"]) -> bool:
    match mode:
        case "nodes": return set(EXPECTED_NODES_CSV_FIELDS).issubset(fields)
        case "links": return set(EXPECTED_LINKS_CSV_FIELDS).issubset(fields)
        case "interfaces": return set(EXPECTED_INTERFACES_CSV_FIELDS).issubset(fields)

class NetworkTopology:
    def __init__(self, name: str, group: str, inputs_dir: str):
        self.name = name if name else "my-network"  # assigns containerlab name
        self.nodes: dict = {}
        self.links: list[dict] = []

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

                        current_device = group_vars_data["devices"].setdefault(row["name"], {"roles": roles})

                        interfaces = current_device.setdefault("interfaces", {})
                        interface = interfaces.setdefault(row["interface"], {})

                        # assign IP address
                        interface["ip_address"] = row["ip_address"]

                        # assign OSPF area
                        if row["ospf_area"]: interface["ospf_area"]= int(row["ospf_area"])
                        
                    with open(self.output_group_vars_file, "w") as f:
                        yaml.dump(group_vars_data, f)
        else:
            print("interfaces.csv not detected")


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
                    self.links = links
                else: 
                    raise ValueError("Input header fields are inconsistent")
        except Exception as e: print(e)
    
    def parse_nodes_csv(self):
        try:
            with open(self.nodes_file_path, mode="r", newline="") as nodes_file:
                reader = csv.DictReader(nodes_file)
                fields = reader.fieldnames or []
                
                if _validate_fieldnames(set(fields), "nodes"):            
                    for row in reader: 
                        kind = "linux"
                        match row["type"]:
                            case "router": self.nodes[row["name"]] = {
                                    "kind": kind, 
                                    "image": DEFAULT_ROUTER_IMAGE,
                                }
                            case "host": self.nodes[row["name"]] = {
                                    "kind": kind, 
                                    "image": DEFAULT_HOST_IMAGE,
                                }
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
    topology.to_clab_yml()

    print("*** Successfully defined topology ***\n")