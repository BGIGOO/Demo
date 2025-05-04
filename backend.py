from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Cho phép truy cập từ frontend

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/route')
def get_route():
    # Đây là demo đơn giản – bạn nên thay bằng thuật toán A*
    orig_lat = float(request.args.get('orig_lat'))
    orig_lon = float(request.args.get('orig_lon'))
    dest_lat = float(request.args.get('dest_lat'))
    dest_lon = float(request.args.get('dest_lon'))

    # Giả sử trả về một tuyến đường đơn giản (thay bằng A* sau)
    return jsonify({
        'route': [
            [orig_lat, orig_lon],
            [(orig_lat + dest_lat)/2, (orig_lon + dest_lon)/2],
            [dest_lat, dest_lon]
        ]
    })

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('.', 'favicon.ico')

if __name__ == '__main__':
    app.run(debug=True)
