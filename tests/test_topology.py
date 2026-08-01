from pathlib import Path
from utils.builder import NetworkTopology

import pytest

TOPOLOGIES_FOLDER = "topologies"

def test_topology():
    base_dir = Path(TOPOLOGIES_FOLDER)
    assert base_dir.exists(), f"{base_dir} does not exist"

    failures = []

    # inputs is string path of inputs folder
    # e.g. topologies/ospf/inputs
    for inputs in base_dir.rglob("inputs"):  
        topology_dir = inputs.parent

        if not inputs.exists():
            failures.append(f"{topology_dir.name}: missing inputs/ directory")
            continue

        try:
            NetworkTopology(
                name=topology_dir.name,
                group="test",
                inputs_dir=str(inputs),
                validate=True,
                write_files=False,
                switch_kind="arista_ceos",

                nodes_file_path=inputs / "nodes.csv",
                links_file_path=inputs / "links.csv",
                interfaces_file_path=inputs / "interfaces.csv",

                ospf_file_path=inputs / "ospf.yml",
                bgp_file_path=inputs / "bgp.yml",
                policy_file_path=inputs / "routing_policy.yml",
            )

        except Exception as e:
            failures.append(f"{topology_dir.name}: {e}")

    if failures:
        pytest.fail("\n\n".join(failures), pytrace=False)
