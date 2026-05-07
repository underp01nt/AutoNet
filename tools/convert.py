# convert raw CSV data into a Containerlab topology
from typing import Literal

import yaml, csv
import argparse

EXPECTED_NODES_CSV_FIELDS = ["name", "type"]
EXPECTED_INTERFACE_CSV_FIELDS = ["name", "interface", "ip_address"]
EXPECTED_LINKS_CSV_FIELDS = ["device_a", "interface_a", "device_b", "interface_b"]

DEFAULT_ROUTER_IMAGE = "frrouting/frr:latest"
DEFAULT_HOST_IMAGE = "alpine:latest"

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
            yaml.dump(self.data, file, sort_keys=False)

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

"""
    interface_planning.csv
    name,interface,ip_address
    pc1,eth1,10.0.1.2/24
    r1,eth1,10.0.1.1/24
    r1,eth2,10.0.2.1/30
    r2,eth1,10.0.2.2/30
    r2,eth2,10.0.4.2/30
    r4,eth2,10.0.4.1/30
    r4,eth1,10.0.6.1/24
    pc2,eth1,10.0.6.2/24
    r3,eth1,10.0.5.2/30
    r4,eth3,10.0.5.1/30
    r1,eth3,10.0.3.1/30
    r3,eth2,10.0.3.2/30
"""
