import osmnx as ox
import os

# Download road network
place_name = "Nashik, Maharashtra, India"
G = ox.graph_from_place(place_name, network_type="drive")

# Convert graph into GeoDataFrames
nodes, edges = ox.graph_to_gdfs(G)

# Create folders if they don't exist
os.makedirs("data/raw", exist_ok=True)

# Save datasets
nodes.to_csv("data/raw/nodes.csv")
edges.to_csv("data/raw/edges.csv")

print("Nodes:", len(nodes))
print("Edges:", len(edges))

print("\nNodes Columns:")
print(nodes.columns)

print("\nEdges Columns:")
print(edges.columns)