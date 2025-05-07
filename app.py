import osmnx as ox
from sklearn.metrics.pairwise import euclidean_distances
import numpy as np
# import networkx as nx # Không dùng trực tiếp cho A* nữa
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import heapq # Sử dụng cho priority queue (open_set)

app = Flask(__name__)
CORS(app)

# Tải bản đồ đường đi (ví dụ: quanh một điểm ở TP.HCM)
# Để quá trình phát triển nhanh hơn, bạn có thể giảm `dist` tạm thời
print("Đang tải bản đồ đường phố...")
G = ox.graph_from_point((10.847874, 106.791798), dist=3000, network_type='drive', simplify=True)
print("Tải bản đồ xong.")

# API: Trả về file HTML chính
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# API: Trả về ranh giới của bản đồ
@app.route('/bounds')
def get_bounds():
    try:
        # OSMnx trả về đồ thị dưới dạng networkx.MultiDiGraph
        # Chuyển đổi sang GeoDataFrames để lấy total_bounds
        _, gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
        bounds = gdf_edges.total_bounds
        # Trả về ranh giới dưới dạng [south, west, north, east]
        return jsonify({'bounds': [bounds[1], bounds[0], bounds[3], bounds[2]]})
    except Exception as e:
        print(f"Lỗi khi lấy bounds: {e}")
        # Lấy ranh giới từ các nút nếu không có cạnh nào (ít khả năng xảy ra với dist > 0)
        min_lon, min_lat, max_lon, max_lat = (None, None, None, None)
        if G.nodes:
            xs = [data['x'] for node, data in G.nodes(data=True)]
            ys = [data['y'] for node, data in G.nodes(data=True)]
            min_lon, min_lat, max_lon, max_lat = min(xs), min(ys), max(xs), max(ys)
            return jsonify({'bounds': [min_lat, min_lon, max_lat, max_lon]})
        return jsonify({'error': str(e), 'message': 'Không thể lấy ranh giới đồ thị'}), 500


# Hàm heuristic: dùng khoảng cách Euclidean giữa 2 node
# Đã sửa: nhận `graph` làm tham số
def heuristic(graph, u_id, v_id):
    # Kiểm tra xem các node có tồn tại trong đồ thị không
    if u_id not in graph.nodes or v_id not in graph.nodes:
        # Trả về giá trị lớn nếu một trong các node không tồn tại,
        # hoặc xử lý lỗi tùy theo yêu cầu
        return float('inf')
    
    u_node_data = graph.nodes[u_id]
    v_node_data = graph.nodes[v_id]
    
    # Kiểm tra xem 'x', 'y' có trong dữ liệu node không
    if 'x' not in u_node_data or 'y' not in u_node_data or \
       'x' not in v_node_data or 'y' not in v_node_data:
        # Xử lý trường hợp thiếu tọa độ
        # print(f"Cảnh báo: Thiếu tọa độ cho node {u_id} hoặc {v_id}")
        return float('inf') # Hoặc một giá trị mặc định khác

    u_point = np.array([[u_node_data['y'], u_node_data['x']]])
    v_point = np.array([[v_node_data['y'], v_node_data['x']]])
    return euclidean_distances(u_point, v_point)[0][0]

# Hàm A* tự viết
def astar_path_custom(graph, start_node, end_node, heuristic_func, weight='length'):
    # open_set là một priority queue, lưu trữ (f_score, node_id)
    open_set = []
    heapq.heappush(open_set, (0, start_node)) # (f_score ước tính, node_id)

    # Dùng set để theo dõi các node có trong open_set (heapq) để kiểm tra nhanh hơn
    open_set_lookup = {start_node}

    # came_from[n] là nút ngay trước n trên đường đi từ start_node đến n rẻ nhất hiện tại.
    came_from = {}

    # g_score[n] là chi phí từ start_node đến n rẻ nhất hiện tại.
    # Khởi tạo với giá trị vô cùng lớn cho tất cả các nút.
    g_score = {node: float('inf') for node in graph.nodes()}
    g_score[start_node] = 0

    # f_score[n] = g_score[n] + heuristic_func(graph, n, end_node).
    # Ước tính tổng chi phí từ start_node đến end_node qua n.
    f_score = {node: float('inf') for node in graph.nodes()}
    f_score[start_node] = heuristic_func(graph, start_node, end_node)

    while open_set:
        # Lấy nút trong open_set có f_score nhỏ nhất
        # current_f, current_node = heapq.heappop(open_set)
        # Nếu dùng current_f, cần kiểm tra xem có phải là f_score lỗi thời không
        # bằng cách so sánh với f_score[current_node] đã lưu.
        # Cách đơn giản hơn là chỉ lấy current_node.
        _, current_node = heapq.heappop(open_set)
        
        if current_node not in open_set_lookup: # Đã được pop và xử lý trước đó bởi một đường đi tốt hơn (nếu có bản sao trong heap)
            continue
        open_set_lookup.remove(current_node) # Đánh dấu là đã lấy ra xử lý


        if current_node == end_node:
            # Đã tìm thấy đường đi, dựng lại đường đi
            path = []
            temp = current_node
            # Nút bắt đầu không có trong came_from theo định nghĩa
            while temp in came_from:
                path.append(temp)
                temp = came_from[temp]
            path.append(start_node) # Thêm nút bắt đầu vào cuối
            return path[::-1] # Đảo ngược để có thứ tự từ start đến end

        # Duyệt qua các nút lân cận của current_node
        for neighbor in graph.neighbors(current_node):
            # Trọng số của cạnh giữa current_node và neighbor
            # G là MultiDiGraph, G.get_edge_data trả về dict các cạnh giữa 2 nút
            # Ví dụ: {0: {'length': 10.5}, 1: {'length': 12.0}} (nếu có nhiều cạnh)
            # Ta nên chọn cạnh có trọng số nhỏ nhất nếu có nhiều.
            edge_data_dict = graph.get_edge_data(current_node, neighbor)
            if not edge_data_dict: # Không có cạnh trực tiếp (không nên xảy ra với graph.neighbors)
                continue

            min_edge_weight = float('inf')
            # Tìm cạnh có 'weight' (ví dụ 'length') nhỏ nhất trong số các cạnh song song
            for edge_key in edge_data_dict:
                edge_attributes = edge_data_dict[edge_key]
                if weight in edge_attributes:
                    min_edge_weight = min(min_edge_weight, edge_attributes[weight])
            
            if min_edge_weight == float('inf'): # Không có cạnh nào có thuộc tính 'weight'
                # print(f"Cảnh báo: Thuộc tính '{weight}' không tìm thấy cho cạnh giữa {current_node} và {neighbor}.")
                continue

            tentative_g_score = g_score[current_node] + min_edge_weight

            if tentative_g_score < g_score.get(neighbor, float('inf')):
                # Đây là đường đi tốt hơn đến neighbor. Ghi lại nó!
                came_from[neighbor] = current_node
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic_func(graph, neighbor, end_node)
                if neighbor not in open_set_lookup:
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
                    open_set_lookup.add(neighbor)
                # else:
                    # Nếu neighbor đã có trong open_set (nghĩa là trong open_set_lookup)
                    # và ta tìm thấy đường đi tốt hơn (f_score mới < f_score cũ),
                    # heapq không có hàm update_priority trực tiếp.
                    # Việc push lại (như một số triển khai) sẽ tạo bản sao trong heap.
                    # Cách tiếp cận hiện tại (không push lại nếu đã trong open_set_lookup nhưng
                    # cập nhật f_score[neighbor]) dựa vào việc khi pop,
                    # ta sẽ lấy được bản có f_score tốt nhất trong số các bản sao.
                    # Tuy nhiên, để đơn giản và tránh nhiều bản sao, cách hiện tại với
                    # open_set_lookup và chỉ push nếu 'not in open_set_lookup' là phổ biến.
                    # Điều quan trọng là f_score[neighbor] được cập nhật.
                    # Một cải tiến nhỏ có thể là push lại nếu f_score được cải thiện, chấp nhận bản sao.
                    # heapq.heappush(open_set, (f_score[neighbor], neighbor))
                    # open_set_lookup.add(neighbor) # Đảm bảo nó vẫn trong lookup nếu push lại


    # Nếu open_set rỗng nhưng không tìm thấy end_node, nghĩa là không có đường đi
    return None # Không tìm thấy đường đi

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
        orig_node = ox.distance.nearest_nodes(G, X=orig_lon, Y=orig_lat)
        dest_node = ox.distance.nearest_nodes(G, X=dest_lon, Y=dest_lat)

        # Kiểm tra nếu orig_node hoặc dest_node không tìm thấy (ví dụ, nếu G rỗng)
        if orig_node is None or dest_node is None:
             return jsonify({'error': 'Không thể tìm thấy nút bắt đầu hoặc kết thúc trên bản đồ.'}), 400
        
        if orig_node == dest_node:
             # Lấy tọa độ của điểm đó
             node_coords = (G.nodes[orig_node]['y'], G.nodes[orig_node]['x'])
             return jsonify({'route': [node_coords], 'message': 'Điểm bắt đầu và kết thúc trùng nhau.'})

        # Tìm đường bằng A* tự viết
        # Truyền G vào heuristic vì nó không còn là phương thức của đối tượng G khi gọi từ bên ngoài
        route_nodes = astar_path_custom(G, orig_node, dest_node, heuristic_func=heuristic, weight='length')

        if route_nodes is None:
            return jsonify({'error': 'Không tìm thấy đường đi giữa hai điểm đã cho.'}), 404

        # Lấy danh sách tọa độ của các điểm trên đường đi
        route_coords = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route_nodes]

        return jsonify({'route': route_coords})
    except ValueError as ve: # Lỗi khi chuyển đổi sang float
        return jsonify({'error': f'Dữ liệu đầu vào không hợp lệ: {ve}'}), 400
    except Exception as e:
        print(f"Lỗi trong API /route: {e}") # Log lỗi ra console server
        return jsonify({'error': f'Đã xảy ra lỗi không mong muốn: {type(e).__name__} - {str(e)}'}), 500

if __name__ == '__main__':
    # `debug=True` sẽ tự động tải lại server khi bạn thay đổi mã.
    # Việc tải bản đồ `G` có thể mất thời gian, nên nó sẽ chạy lại mỗi lần tải lại.
    # Để tránh điều này trong quá trình phát triển, bạn có thể:
    # 1. Tải `G` một lần và truyền vào các hàm nếu cần (khó với cấu trúc Flask hiện tại).
    # 2. Sử dụng `app.run(debug=True, use_reloader=False)` để tắt reloader nhưng vẫn giữ chế độ debug.
    # Tuy nhiên, reloader rất tiện cho việc phát triển.
    app.run(debug=True)
