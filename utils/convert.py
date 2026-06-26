from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq
from typing import Literal
import os, csv, argparse

EXPECTED_NODES_CSV_FIELDS = ["name", "type"]
EXPECTED_INTERFACE_CSV_FIELDS = ["name", "interface", "ip_address"]
EXPECTED_LINKS_CSV_FIELDS = ["device_a", "interface_a", "device_b", "interface_b"]

DEFAULT_ROUTER_IMAGE = "frrouting/frr:latest"
DEFAULT_HOST_IMAGE = "alpine:latest"

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)

class NetworkTopology:
    def __init__(self, name: str, inputs_dir: str):
        self.name = name if name else "my-network"  # assigns containerlab name
        self.nodes: dict = {}
        self.links: list[dict] = []

        # I/O related attributes
        self.main_dir = Path(inputs_dir).parent
        self.output_file = self.main_dir / f"{self.name}.clab.yml"

    def to_clab_yml(self): 
        with open(self.output_file, "w") as file:
            self.data = {
                "name": self.name, 
                "topology": {"nodes": self.nodes, "links": self.links}
            }
            yaml.dump(self.data, file)

def validate_fieldnames(fields: set, mode: Literal["nodes", "links"]) -> bool:
    match mode:
        case "nodes": return fields.issubset(set(EXPECTED_NODES_CSV_FIELDS))
        case "links": return fields.issubset(set(EXPECTED_LINKS_CSV_FIELDS))

def parse_links_csv(file_path: str, topology: NetworkTopology):
    try:
        with open(file_path, mode="r", newline="") as file:
            reader = csv.DictReader(file)
            fields = reader.fieldnames or []
            if validate_fieldnames(set(fields), "links"):
                links = []
                for row in reader:
                    endpt_A = f"{row['device_a']}:{row['interface_a']}"
                    endpt_B = f"{row['device_b']}:{row['interface_b']}"
                    
                    endpoints = CommentedSeq([endpt_A, endpt_B])
                    endpoints.fa.set_flow_style()
                    
                    links.append({"endpoints": endpoints})
                topology.links = links
            else: 
                raise ValueError("Input header fields are inconsistent")
    except Exception as e: print(e)
    
def parse_nodes_csv(file_path: str, topology: NetworkTopology):
    try:
        with open(file_path, mode="r", newline="") as file:
            reader = csv.DictReader(file)
            fields = reader.fieldnames or []
            if validate_fieldnames(set(fields), "nodes"):            
                for row in reader: 
                    kind = "linux"
                    match row["type"]:
                        case "router": topology.nodes[row["name"]] = {
                                "kind": kind, 
                                "image": DEFAULT_ROUTER_IMAGE,
                            }
                        case "host": topology.nodes[row["name"]] = {
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
    args = parser.parse_args()

    nodes_file = os.path.join(args.inputs, "nodes.csv")
    links_file = os.path.join(args.inputs, "links.csv")

    if not args.name:
        raise ValueError("Please provide a topology name")
    
    topology = NetworkTopology(args.name, args.inputs)
    if os.path.exists(nodes_file): parse_nodes_csv(nodes_file, topology)
    if os.path.exists(links_file): parse_links_csv(links_file, topology)

    topology.to_clab_yml()
