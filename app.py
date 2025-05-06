import osmnx as ox
from sklearn.metrics.pairwise import euclidean_distances
import numpy as np
import networkx as nx
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Tải bản đồ đường đi bộ quanh tọa độ (SG)
print("Đang tải bản đồ đường phố...")
G = ox.graph_from_point((10.847874, 106.791798), dist=1500, network_type='drive', simplify=True)
print("Tải bản đồ xong.")

# API: Trả về file HTML chính
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# API: Trả về ranh giới của bản đồ
@app.route('/bounds')
def get_bounds():
    # Lấy ranh giới của đồ thị
    bounds = ox.graph_to_gdfs(G, nodes=False, edges=False).total_bounds
    # Trả về ranh giới dưới dạng [south, west, north, east]
    return jsonify({'bounds': [bounds[1], bounds[0], bounds[3], bounds[2]]})

# Hàm heuristic: dùng khoảng cách Euclidean giữa 2 node
def heuristic(u, v):
    u_point = np.array([[G.nodes[u]['y'], G.nodes[u]['x']]])
    v_point = np.array([[G.nodes[v]['y'], G.nodes[v]['x']]])
    return euclidean_distances(u_point, v_point)[0][0]

# API: Tìm đường đi giữa 2 điểm
@app.route('/route')
def get_route():
    try:
        # Lấy tọa độ từ query parameters
        orig_lat = float(request.args.get('orig_lat'))
        orig_lon = float(request.args.get('orig_lon'))
        dest_lat = float(request.args.get('dest_lat'))
        dest_lon = float(request.args.get('dest_lon'))

        # Tìm node gần nhất với điểm xuất phát và đích
        orig_node = ox.distance.nearest_nodes(G, orig_lon, orig_lat)
        dest_node = ox.distance.nearest_nodes(G, dest_lon, dest_lat)

        # Tìm đường bằng A*
        route = nx.astar_path(G, orig_node, dest_node, heuristic=heuristic, weight='length')

        # Lấy danh sách tọa độ của các điểm trên đường đi
        route_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route]

        return jsonify({'route': route_coords})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
