import redis
import threading
import time
import random
from typing import Dict, List, Optional

class VectorClock:
    """Vector clock for tracking causality in distributed systems."""
    def __init__(self, nodes: List[str]):
        self.clock = {node: 0 for node in nodes}

    def increment(self, node: str):
        """Increment the clock for the given node."""
        self.clock[node] += 1

    def update(self, other: Dict[str, int]):
        """Update the clock with the maximum values from another clock."""
        for node, ts in other.items():
            self.clock[node] = max(self.clock.get(node, 0), ts)

    def get(self):
        """Get a copy of the current clock."""
        return self.clock.copy()

class Node:
    """Represents a node in the distributed system."""
    def __init__(self, name: str, redis_host: str, redis_port: int, nodes: List[str]):
        self.name = name
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.nodes = nodes
        self.vector_clock = VectorClock(nodes)
        self.is_leader = False
        self.alive = True
        self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port, decode_responses=True)

    def health_check(self):
        """Check if the Redis node is alive."""
        try:
            return self.redis_client.ping()
        except Exception:
            return False

    def update_status(self):
        """Update the alive status of the node."""
        self.alive = self.health_check()

class CoordinatorRing:
    """Coordinator ring for managing distributed nodes with leader election."""
    def __init__(self, node_configs: Dict[str, Dict[str, any]]):
        node_names = list(node_configs.keys())
        self.nodes = {name: Node(name, config['host'], config['port'], node_names) for name, config in node_configs.items()}
        self.ring = list(self.nodes.keys())
        self.leader = None
        self.lock = threading.Lock()
        self._elect_leader()

    def _elect_leader(self):
        """Elect the leader as the lowest alive node."""
        alive_nodes = [n for n in self.ring if self.nodes[n].alive]
        if alive_nodes:
            self.leader = min(alive_nodes)
            for n in self.ring:
                self.nodes[n].is_leader = (n == self.leader)
        else:
            self.leader = None

    def vector_clock(self, node: str):
        """Get the vector clock for the given node."""
        return self.nodes[node].vector_clock.get()

    def write(self, key: str, value: str):
        """Write key-value pair to the leader node."""
        with self.lock:
            if not self.leader:
                raise Exception("No leader available")
            node = self.leader
            self.nodes[node].vector_clock.increment(node)
            vc = self.nodes[node].vector_clock.get()
            self.nodes[node].redis_client.set(key, value)
            self.nodes[node].redis_client.set(f"vc:{key}", str(vc))
            return True

    def read(self, key: str):
        """Read value for the key from the leader node."""
        if not self.leader:
            raise Exception("No leader available")
        node = self.leader
        value = self.nodes[node].redis_client.get(key)
        vc = self.nodes[node].redis_client.get(f"vc:{key}")
        return value, vc

    def health_monitor(self):
        """Monitor node health and elect leader periodically."""
        while True:
            for n in self.ring:
                self.nodes[n].update_status()
            self._elect_leader()
            time.sleep(2)

    def exclude_failed_nodes(self):
        """Remove failed nodes from the ring."""
        self.ring = [n for n in self.ring if self.nodes[n].alive]

    def start_health_thread(self):
        """Start the health monitoring thread."""
        t = threading.Thread(target=self.health_monitor, daemon=True)
        t.start()

# Example usage
if __name__ == "__main__":
    node_ports = {
        "node1": 6379,
        "node2": 6380,
        "node3": 6381
    }
    ring = CoordinatorRing(node_ports)
    ring.start_health_thread()
    time.sleep(3)
    print("Leader:", ring.leader)
    ring.write("foo", "bar")
    print("Read:", ring.read("foo"))
    print("Vector Clock:", ring.vector_clock(ring.leader))
