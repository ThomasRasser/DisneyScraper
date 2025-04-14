import json
import os
import sys

import matplotlib.pyplot as plt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import (
    BIGGEST_ISLAND_PATH,
    COMBINED_ATTRACTION_DATA_PATH,
    COMBINED_DINING_DATA_PATH,
    NODE_ISLAND_IMG_PATH,
    NODE_ISLAND_IMG_PATH_TSP,
    clean_path,
)
from utils.save_load import (
    load_json_data_cached,
    load_osm_data,
)


# region Constants
class Node:
    def __init__(self, node_id, connected_nodes=None, lat=None, lon=None, name=None):
        self.node_id = node_id
        self.connected_nodes = set(connected_nodes or [])
        self.connected_split_nodes = set()
        # Split nodes are nodes with more than 2 connections.
        # ---------------------------------------
        # These nodes are used for TSP,
        # therefore the "neighbor" is not the immediate neighbor,
        # but the next node in this path, which is a split node.
        self.lat = lat
        self.lon = lon
        self.name = name

    def __repr__(self):
        name_str = f", name={self.name}" if self.name else ""
        return f"Node(node_id={self.node_id}, connected_nodes={self.connected_nodes}{name_str})"

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "connected_nodes": list(self.connected_nodes),
            "connected_split_nodes": list(self.connected_split_nodes),
            "lat": self.lat,
            "lon": self.lon,
            "name": self.name,
        }

    def __eq__(self, other):
        if not isinstance(other, Node):
            return NotImplemented
        return self.node_id == other.node_id


class NodeIsland:
    def __init__(self, nodes: list[Node] | Node):
        if isinstance(nodes, Node):
            nodes = [nodes]
        elif not isinstance(nodes, list):
            raise TypeError("nodes must be a Node or a list of Nodes")
        self.nodes = nodes
        self.size = len(nodes)
        self.names = []  # List to store names of nodes in this island

        # Collect all names from nodes
        for node in nodes:
            if node.name and node.name not in self.names:
                self.names.append(node.name)

    def add_node(self, node: Node):
        self.nodes.append(node)
        self.size += 1
        # Add node name to names list if it has one and isn't already in the list
        if node.name and node.name not in self.names:
            self.names.append(node.name)

    def __repr__(self):
        # Show the size of the island and any names it contains
        names_str = f", names={self.names}" if self.names else ""
        return f"NodeIsland(size={self.size}{names_str})"

    def to_dict(self):
        return {
            "size": self.size,
            "nodes": [node.node_id for node in self.nodes],
            "names": self.names,  # Include names in dict representation
        }

    def __len__(self):
        return self.size


# endregion


# Node and NodeIsland manipulation functions
def create_node_connections(osm_data: list[dict]) -> dict[str, Node]:
    """
    Build a graph of nodes based on their sequential appearance in ways.
    :param osm_data: OSM data, expected to be a list of ways with 'nodes'.
    :return: Dictionary mapping node_id to Node instances.
    """
    print("Creating node connections")
    node_connections: dict[str, Node] = {}

    # First pass: extract node coordinates and names
    node_coords = {}
    node_names = {}
    for element in osm_data:
        if element.get("type") == "node":
            node_id = element.get("id")
            lat = element.get("lat")
            lon = element.get("lon")

            # Extract name from tags if available
            tags = element.get("tags", {})
            name = tags.get("name")

            if node_id is not None and lat is not None and lon is not None:
                node_coords[str(node_id)] = (float(lat), float(lon))
                if name:
                    node_names[str(node_id)] = name

    print(f"Found {len(node_coords)} nodes with coordinates")
    print(f"Found {len(node_names)} nodes with names")

    # Second pass: create connections from ways
    for way in osm_data:
        node_type = way.get("type")
        if node_type != "way":
            continue

        # Extract way name if available
        way_name = None
        way_tags = way.get("tags", {})
        if way_tags:
            way_name = way_tags.get("name")

        node_ids = way.get("nodes")
        if not node_ids:
            continue

        for i in range(len(node_ids)):
            node_id = str(node_ids[i])

            # Get node name from node or way
            node_name = node_names.get(node_id)
            if not node_name and way_name:
                node_name = way_name

            # Create or get node
            if node_id not in node_connections:
                lat, lon = None, None
                if node_id in node_coords:
                    lat, lon = node_coords[node_id]
                node_connections[node_id] = Node(node_id, lat=lat, lon=lon, name=node_name)
            elif node_name and not node_connections[node_id].name:
                # Update node name if we have one now
                node_connections[node_id].name = node_name

            # Connect to previous node in the way
            if i > 0:
                prev_node_id = str(node_ids[i - 1])
                node_connections[node_id].connected_nodes.add(prev_node_id)

                # Get name for previous node
                prev_node_name = node_names.get(prev_node_id)
                if not prev_node_name and way_name:
                    prev_node_name = way_name

                # Create previous node if it doesn't exist
                if prev_node_id not in node_connections:
                    lat, lon = None, None
                    if prev_node_id in node_coords:
                        lat, lon = node_coords[prev_node_id]
                    node_connections[prev_node_id] = Node(prev_node_id, lat=lat, lon=lon, name=prev_node_name)
                elif prev_node_name and not node_connections[prev_node_id].name:
                    # Update node name if we have one now
                    node_connections[prev_node_id].name = prev_node_name

                # Add the connection in both directions
                node_connections[prev_node_id].connected_nodes.add(node_id)

    return node_connections


def find_node_islands(node_connections: dict[str, Node]) -> list[NodeIsland]:
    """
    Find disconnected clusters (islands) of nodes.
    :param node_connections: Graph of node connections.
    :return: List of NodeIsland objects.
    """
    print("Finding islands of nodes")

    visited = set()
    islands: list[NodeIsland] = []

    for node_id in node_connections:
        if node_id not in visited:
            # Create a new island
            current_island_nodes = []
            stack = [node_id]

            # Use DFS to find all connected nodes
            while stack:
                current = stack.pop()
                if current not in visited:
                    visited.add(current)
                    current_node = node_connections[current]
                    current_island_nodes.append(current_node)
                    stack.extend(current_node.connected_nodes - visited)

            # Create a NodeIsland with all discovered nodes
            island = NodeIsland(current_island_nodes)
            islands.append(island)

    print(f"Found {len(islands)} islands of nodes")

    # Sort islands by size
    islands.sort(key=len, reverse=True)

    # Save island as JSON
    island_data = [island.to_dict() for island in islands]
    with open(NODE_ISLAND_PATH, "w", encoding="utf-8") as f:
        json.dump(island_data, f, indent=4, ensure_ascii=False)
    print(f"Saved islands to {NODE_ISLAND_PATH}")

    return islands


def find_split_neighbors_dfs(node_connections):
    """
    Using depth-first search, find all connected split nodes for each node.
    A split node is a node with more than 2 connections.

    :param node_connections: Dictionary mapping node_id to Node objects
    """
    print("Finding split neighbors using DFS...")

    # Function to check if a node is a split node
    def is_split_node(node_id):
        node = node_connections.get(node_id)
        return node and len(node.connected_nodes) > 2

    # DFS function to find next split node in each direction
    def dfs_find_next_split(current_id, visited=None, path=None):
        if visited is None:
            visited = set()
        if path is None:
            path = []

        # Mark current node as visited
        visited.add(current_id)

        current_node = node_connections.get(current_id)
        if not current_node:
            return None

        # Check neighbors
        for neighbor_id in current_node.connected_nodes:
            # Skip already visited nodes to avoid cycles
            if neighbor_id in visited:
                continue

            # Check if this neighbor is a split node
            if is_split_node(neighbor_id):
                return neighbor_id

            # If not a split node, continue DFS
            result = dfs_find_next_split(neighbor_id, visited.copy(), path + [neighbor_id])
            if result:
                return result

        return None

    # Process each node
    count = 0
    for node_id, node in node_connections.items():
        # For each neighbor direction
        for neighbor_id in node.connected_nodes:
            # Skip if this neighbor is already a split node
            if is_split_node(neighbor_id):
                node.connected_split_nodes.add(neighbor_id)
                continue

            # Start DFS from this neighbor
            visited = {node_id}  # Don't go back to the starting node
            split_node = dfs_find_next_split(neighbor_id, visited)

            # If we found a split node, add it
            if split_node:
                node.connected_split_nodes.add(split_node)

        count += 1
        if count % 1000 == 0:
            print(f"Processed {count} nodes")

    print(f"Completed finding split neighbors for {count} nodes")


def update_island_with_split_neighbors(islands, node_connections):
    """
    Update all islands with split neighbor information.

    :param islands: List of NodeIsland objects
    :param node_connections: Dictionary mapping node_id to Node objects
    """
    # Find all split neighbors
    find_split_neighbors_dfs(node_connections)

    # No need to update the islands, as node_connections are already updated
    print("Islands updated with split neighbor information")


# endregion


# Node and NodeIsland export functions
def export_biggest_island_to_json(islands, node_connections, output_path=BIGGEST_ISLAND_PATH):
    """
    Export the biggest island to a JSON format suitable for database import.

    :param islands: List of NodeIsland objects, sorted by size
    :param node_connections: Dictionary mapping node_id to Node objects
    :param output_path: Path to save the JSON file
    """
    if not islands:
        print("No islands to export")
        return

    # Take the biggest island
    biggest_island = islands[0]
    print(f"Exporting biggest island with {len(biggest_island)} nodes")

    # Create the export structure
    export_data = {"biggest_island": {"nodes": []}}

    # Count split nodes
    split_nodes_count = sum(1 for node in biggest_island.nodes if len(node.connected_nodes) > 2)
    print(f"Found {split_nodes_count} split nodes in the biggest island")

    # Process each node in the biggest island
    for node in biggest_island.nodes:
        # Skip nodes without coordinates
        if node.lat is None or node.lon is None:
            continue

        # Determine a basic node type - this is a placeholder, modify as needed
        node_type = "intersection"  # Default type
        if len(node.connected_nodes) == 1:
            node_type = "endpoint"
        elif len(node.connected_nodes) > 2:
            node_type = "junction"

        # Add node to export data
        node_data = {
            "id": node.node_id,
            "type": node_type,
            "latitude": node.lat,
            "longitude": node.lon,
            "neighbors": list(node.connected_nodes),
            "split_neighbors": list(node.connected_split_nodes),
        }

        # Add name if available
        if node.name:
            node_data["name"] = node.name

        export_data["biggest_island"]["nodes"].append(node_data)

    # Save to JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(export_data['biggest_island']['nodes'])} nodes to {output_path}")

    return export_data


def draw_islands_V1(node_connections, islands, max_islands=25):
    """
    Visualize islands using matplotlib, with each island in a different color.

    :param node_connections: Dictionary mapping node IDs to Node objects with lat/lon
    :param islands: List of NodeIsland objects
    :param max_islands: Maximum number of islands to draw
    """

    # NOTE:
    # I wasn't sure if it was possible to traverse the path with our given nodes,
    # so I decided to use matplotlib to visualize the islands.
    # Output:
    # Best-case: A single island with all nodes connected
    # Worst-case: Multiple islands with no connections
    #
    # Luckily, there was one island encompassing most nodes,
    # and the  other island with reasonably size, where based on the mapping,
    # of a singular attraction, which is not accessible by foot.
    # ...at least thats what i saw

    print("Drawing islands using matplotlib")

    # Find bounding box for scaling
    min_lat, max_lat = float("inf"), float("-inf")
    min_lon, max_lon = float("inf"), float("-inf")

    # Check which nodes have coordinates
    nodes_with_coords = 0
    for node_id, node in node_connections.items():
        if node.lat is not None and node.lon is not None:
            nodes_with_coords += 1
            min_lat = min(min_lat, node.lat)
            max_lat = max(max_lat, node.lat)
            min_lon = min(min_lon, node.lon)
            max_lon = max(max_lon, node.lon)

    print(f"Found {nodes_with_coords} nodes with coordinates out of {len(node_connections)} total nodes")

    if nodes_with_coords == 0:
        print("No nodes have coordinates. Cannot create visualization.")
        return

    # Create figure and axes
    plt.figure(figsize=(12, 10))
    ax = plt.subplot(111)

    # Generate a list of distinct colors for islands
    colors = plt.cm.tab10.colors  # Get distinct colors from a colormap

    # Sort islands by size and take the largest ones
    islands_to_draw = sorted(islands, key=len, reverse=True)[:max_islands]

    # Draw each island
    for i, island in enumerate(islands_to_draw):
        print(f"Drawing island {i + 1} with {len(island)} nodes")

        # Choose color for this island
        color = colors[i % len(colors)]

        # Collect node coordinates for this island
        island_lons = []
        island_lats = []
        for node in island.nodes:
            if node.lat is not None and node.lon is not None:
                island_lons.append(node.lon)
                island_lats.append(node.lat)

        if not island_lons:
            print(f"Island {i + 1} has no nodes with coordinates. Skipping.")
            continue

        # Plot nodes
        ax.scatter(island_lons, island_lats, s=10, color=color, alpha=0.8, label=f"Island {i + 1}: {len(island)} nodes")

        # Draw connections (edges)
        drawn_connections = set()
        for node in island.nodes:
            if node.lat is None or node.lon is None:
                continue

            for connected_id in node.connected_nodes:
                # Create a unique identifier for this connection
                connection = tuple(sorted([node.node_id, connected_id]))

                # Check if we've already drawn this connection
                if connection in drawn_connections:
                    continue

                connected_node = node_connections.get(connected_id)
                if connected_node and connected_node.lat is not None and connected_node.lon is not None:
                    # Draw a line between the nodes
                    ax.plot(
                        [node.lon, connected_node.lon],
                        [node.lat, connected_node.lat],
                        "-",
                        color=color,
                        linewidth=0.5,
                        alpha=0.6,
                    )

                    # Mark this connection as drawn
                    drawn_connections.add(connection)

    # Add title and labels
    plt.title("OSM Node Islands Visualization")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")

    # Add legend with smaller font size and more compact layout
    plt.legend(loc="upper right", bbox_to_anchor=(1.1, 1), fontsize="x-small", markerscale=1, labelspacing=0.3)

    # Make sure the aspect ratio is correct for geographic data
    ax.set_aspect("equal")

    # Adjust plot margins
    plt.tight_layout()

    # Save the plot as an image
    print("Visualization complete. Close the matplotlib window to continue.")
    plt.savefig("node_islands.png", dpi=300, bbox_inches="tight")
    print("Saved visualization to 'node_islands.png'")


def draw_islands(node_connections, islands, max_islands=25, use_split_nodes=False):
    """
    Visualize islands using matplotlib, with each island in a different color.

    :param node_connections: Dictionary mapping node IDs to Node objects with lat/lon
    :param islands: List of NodeIsland objects
    :param max_islands: Maximum number of islands to draw
    :param use_split_nodes: If True, use connected_split_nodes instead of connected_nodes
    """
    import matplotlib.pyplot as plt

    print(f"Drawing islands using {'connected_split_nodes' if use_split_nodes else 'connected_nodes'}")

    min_lat, max_lat = float("inf"), float("-inf")
    min_lon, max_lon = float("inf"), float("-inf")

    nodes_with_coords = 0
    for node in node_connections.values():
        if node.lat is not None and node.lon is not None:
            nodes_with_coords += 1
            min_lat = min(min_lat, node.lat)
            max_lat = max(max_lat, node.lat)
            min_lon = min(min_lon, node.lon)
            max_lon = max(max_lon, node.lon)

    if nodes_with_coords == 0:
        print("No nodes with coordinates. Cannot draw.")
        return

    plt.figure(figsize=(12, 10))
    ax = plt.subplot(111)
    colors = plt.cm.tab10.colors
    islands_to_draw = sorted(islands, key=len, reverse=True)[:max_islands]

    for i, island in enumerate(islands_to_draw):
        color = colors[i % len(colors)]
        island_lats, island_lons = [], []

        for node in island.nodes:
            if node.lat is not None and node.lon is not None:
                island_lats.append(node.lat)
                island_lons.append(node.lon)

        if not island_lons:
            continue

        ax.scatter(island_lons, island_lats, s=10, color=color, alpha=0.8, label=f"Island {i + 1}: {len(island)} nodes")

        drawn_connections = set()
        for node in island.nodes:
            if node.lat is None or node.lon is None:
                continue

            conn_attr = node.connected_split_nodes if use_split_nodes else node.connected_nodes
            for connected_id in conn_attr:
                connection = tuple(sorted([node.node_id, connected_id]))
                if connection in drawn_connections:
                    continue

                connected_node = node_connections.get(connected_id)
                if connected_node and connected_node.lat is not None and connected_node.lon is not None:
                    ax.plot(
                        [node.lon, connected_node.lon],
                        [node.lat, connected_node.lat],
                        "-",
                        color=color,
                        linewidth=0.5,
                        alpha=0.6,
                    )
                    drawn_connections.add(connection)

    plt.title("OSM Node Islands Visualization")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.legend(loc="upper right", bbox_to_anchor=(1.1, 1), fontsize="x-small", markerscale=1, labelspacing=0.3)
    ax.set_aspect("equal")
    plt.tight_layout()

    filename = NODE_ISLAND_IMG_PATH if use_split_nodes else NODE_ISLAND_IMG_PATH_TSP
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    print(f"Saved visualization to '{clean_path(filename)}'")


# endregion


# Main
def main():
    osm_data = load_osm_data()

    node_connections = create_node_connections(osm_data)
    print(f"Found {len(node_connections)} node connections")

    islands = find_node_islands(node_connections)
    print(f"Found {len(islands)} islands of nodes")

    # Filter out islands with less than 3 nodes
    islands = [island for island in islands if len(island) >= 3]
    print(f"Filtered to {len(islands)} islands with at least 3 nodes")

    islands.sort(key=len, reverse=True)
    print("Biggest islands:")
    for i, island in enumerate(islands[:10]):
        print(f"Island {i + 1}: {len(island)} nodes")

    # Find split neighbors
    find_split_neighbors_dfs(node_connections)
    print("Split neighbors found")

    # Update islands with split neighbors
    update_island_with_split_neighbors(islands, node_connections)
    print("Islands updated with split neighbors")

    # Export the biggest island to JSON
    export_biggest_island_to_json(islands, node_connections)
    print("Biggest island exported to JSON")

    # Uncomment to visualize the islands using matplotlib as a PNG image
    draw_islands(node_connections, islands, max_islands=25)
    draw_islands(node_connections, islands, max_islands=25, use_split_nodes=True)


if __name__ == "__main__":
    main()
# endregion
