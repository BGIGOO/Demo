
// Biến giữ đối tượng bản đồ Leaflet
// Đảm bảo bản đồ được khởi tạo sau khi div #map đã có kích thước
const map = L.map('map').setView([10.762622, 106.660172], 17);

// Thêm lớp bản đồ OpenStreetMap
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Mảng chứa các điểm đánh dấu (markers) trên bản đồ
let danhSachDiemDanhDau = [];
// Biến giữ đối tượng đường đi (polyline) vẽ trên bản đồ
let duongDanVe;

// Hàm vẽ đường đi trên bản đồ
function veDuongDi(duongDi) {
  // Nếu đã có đường đi trước đó, xóa nó đi
  if (duongDanVe) map.removeLayer(duongDanVe);
  // Tạo đường polyline mới từ dữ liệu đường đi và thêm vào bản đồ
  duongDanVe = L.polyline(duongDi, { color: 'blue' }).addTo(map);
  // Căn chỉnh bản đồ để hiển thị toàn bộ đường đi
  if (duongDanVe.getBounds().isValid()) { // Kiểm tra bounds hợp lệ trước khi fit
     map.fitBounds(duongDanVe.getBounds());
  }
}

// Hàm thêm một điểm đánh dấu vào bản đồ
function themDiemDanhDau(toaDo, nhan) {
  const diemDanhDau = L.marker(toaDo).addTo(map).bindPopup(nhan).openPopup();
  // Thêm điểm đánh dấu vào danh sách
  danhSachDiemDanhDau.push(diemDanhDau);
}

// Lắng nghe sự kiện click trên bản đồ
map.on('click', function(e) {
  // Nếu đã có 2 điểm đánh dấu, xóa tất cả để bắt đầu lại
  if (danhSachDiemDanhDau.length >= 2) {
    danhSachDiemDanhDau.forEach(diem => map.removeLayer(diem));
    if (duongDanVe) map.removeLayer(duongDanVe);
    danhSachDiemDanhDau = [];
    // Xóa nội dung trong ô input khi làm mới
    $('#startPoint').val('');
    $('#endPoint').val('');
  }

  // Lấy tọa độ từ sự kiện click
  const toaDoClick = [e.latlng.lat, e.latlng.lng];
  const toaDoString = `${toaDoClick[0].toFixed(6)}, ${toaDoClick[1].toFixed(6)}`; // Định dạng tọa độ

  // Thêm điểm đánh dấu tại tọa độ click
  if (danhSachDiemDanhDau.length === 0) {
    // Đây là điểm xuất phát
    themDiemDanhDau(toaDoClick, 'Xuất phát');
    $('#startPoint').val(toaDoString); // Cập nhật ô input điểm xuất phát
  } else if (danhSachDiemDanhDau.length === 1) {
    // Đây là điểm đích
    themDiemDanhDau(toaDoClick, 'Đích');
    $('#endPoint').val(toaDoString); // Cập nhật ô input điểm đích đến
  }


  // Nếu đã có đủ 2 điểm (Xuất phát và Đích)
  if (danhSachDiemDanhDau.length === 2) {
    // Lấy tọa độ của điểm xuất phát và điểm đích
    const [diemBatDau, diemKetThuc] = danhSachDiemDanhDau.map(diem => diem.getLatLng());
    // Tạo URL để gọi API tìm đường (giả định)
    const url = `/route?orig_lat=${diemBatDau.lat}&orig_lon=${diemBatDau.lng}&dest_lat=${diemKetThuc.lat}&dest_lon=${diemKetThuc.lng}`;

    // Gửi yêu cầu GET đến server để lấy dữ liệu đường đi
    // Lưu ý: Đây là URL giả định, bạn cần cài đặt server-side để xử lý yêu cầu này
    // và trả về dữ liệu đường đi (ví dụ: mảng các cặp [lat, lng)).
    // Hiện tại, phần này sẽ không hoạt động nếu không có server xử lý.
    $.getJSON(url, function(duLieu) {
        // Giả định dữ liệu trả về có thuộc tính 'route' là mảng các tọa độ
        if (duLieu && duLieu.route && duLieu.route.length > 0) {
             veDuongDi(duLieu.route);
        } else {
             console.warn("API route không trả về dữ liệu đường đi hợp lệ hoặc không có đường đi.");
             if (duongDanVe) map.removeLayer(duongDanVe); // Xóa đường cũ nếu có
             alert("Không tìm thấy đường đi giữa hai điểm này.");
        }
    }).fail(function(jqxhr, textStatus, error) {
        const err = textStatus + ", " + error;
        console.error("Đã xảy ra lỗi khi gọi API route: " + err);
        if (duongDanVe) map.removeLayer(duongDanVe); // Xóa đường cũ nếu có
        alert("Đã xảy ra lỗi khi tìm đường đi. Vui lòng kiểm tra console log.");
    });
  }
});

// Trình lắng nghe sự kiện cho nút "Chọn trên bản đồ"
$('#selectOnMapButton').on('click', function() {
    alert('Bây giờ hãy click vào bản đồ để chọn điểm Xuất phát (click lần 1) và Đích đến (click lần 2).');
    // Có thể thêm logic để cuộn xuống bản đồ nếu cần
    // map.invalidateSize(); // Cập nhật kích thước bản đồ nếu nó bị ẩn ban đầu
});

// Quan trọng: Gọi invalidateSize() sau khi đảm bảo div bản đồ đã hiển thị và có kích thước.
// Điều này khắc phục sự cố hiển thị bản đồ (chỉ hiển thị một phần nhỏ)
// khi nó nằm trong một layout phức tạp hoặc ban đầu bị ẩn.
// Có thể gọi sau khi trang tải xong hoặc sau khi container của bản đồ hiển thị.
$(window).on('load', function() {
    map.invalidateSize();
});