# convert raw CSV data into a Containerlab topology
from typing import Literal
from ruamel.yaml import YAML
import csv, argparse
import argparse

EXPECTED_NODES_CSV_FIELDS = ["name", "type"]
EXPECTED_INTERFACE_CSV_FIELDS = ["name", "interface", "ip_address"]
EXPECTED_LINKS_CSV_FIELDS = ["device_a", "interface_a", "device_b", "interface_b"]

DEFAULT_ROUTER_IMAGE = "frrouting/frr:latest"
DEFAULT_HOST_IMAGE = "alpine:latest"

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)

class NetworkTopology:
    def __init__(self, name: str):
        self.name = name if name else "my-network"  # assigns containerlab name
        self.nodes: dict = {}
        self.links: list[dict] = []

    def to_clab_yml(self): 
        with open(f"{self.name}.clab.yml", "w") as file:
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
                    links.append({"endpoints": [endpt_A, endpt_B]})
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
    parser.add_argument("-n")       # topology name
    parser.add_argument("-nodes")   # network nodes 
    parser.add_argument("-links")   # node connections
    args = parser.parse_args()

    topology = NetworkTopology(args.n)
    if args.nodes: parse_nodes_csv(args.nodes, topology)
    if args.links: parse_links_csv(args.links, topology)

    topology.to_clab_yml()
