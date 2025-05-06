import osmnx as ox
from sklearn.metrics.pairwise import euclidean_distances
import numpy as np
import networkx as nx
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Tải bản đồ đường đi bộ quanh tọa độ (SG)
print("Đang tải bản đồ đường phố...")
G = ox.graph_from_point((10.762622, 106.660172), dist=1500, network_type='walk', simplify=True)
print("Tải bản đồ xong.")

# Hàm heuristic: dùng khoảng cách Euclidean giữa 2 node
def heuristic(u, v):
    u_point = np.array([[G.nodes[u]['y'], G.nodes[u]['x']]])
    v_point = np.array([[G.nodes[v]['y'], G.nodes[v]['x']]])
    return euclidean_distances(u_point, v_point)[0][0]

@app.route('/route')
def get_route():
    orig_lat = float(request.args.get('orig_lat'))
    orig_lon = float(request.args.get('orig_lon'))
    dest_lat = float(request.args.get('dest_lat'))
    dest_lon = float(request.args.get('dest_lon'))

    orig_node = ox.distance.nearest_nodes(G, orig_lon, orig_lat)
    dest_node = ox.distance.nearest_nodes(G, dest_lon, dest_lat)

    # Tìm đường bằng A*
    route = nx.astar_path(G, orig_node, dest_node, heuristic=heuristic, weight='length')

    route_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]

    return jsonify({'route': route_coords})

if __name__ == '__main__':
    app.run(debug=True)
