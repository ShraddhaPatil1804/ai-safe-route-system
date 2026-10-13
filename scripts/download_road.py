import osmnx as ox

# Download Nashik road network
place_name = "Nashik, Maharashtra, India"

print("Downloading road network...")

G = ox.graph_from_place(place_name, network_type="drive")

print("Download complete!")

print(G)