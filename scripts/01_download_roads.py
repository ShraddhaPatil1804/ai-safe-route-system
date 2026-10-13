import os
import osmnx as ox
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL)

print("Downloading Nashik road network...")

G = ox.graph_from_place(
    "Nashik, Maharashtra, India",
    network_type="drive"
)

print("Converting graph...")

nodes, edges = ox.graph_to_gdfs(G)

print(nodes.head())
print(edges.head())

print(f"Nodes : {len(nodes)}")
print(f"Edges : {len(edges)}")

print("Saving to PostgreSQL...")

nodes.to_postgis(
    "intersections",
    engine,
    if_exists="replace"
)

edges.to_postgis(
    "roads",
    engine,
    if_exists="replace"
)

print("Done!")