
// Biến giữ đối tượng bản đồ Leaflet
// Khởi tạo map sớm, nhưng chưa setView cố định
const map = L.map('map').setView([10.850661, 106.798139], 10);

// Thêm lớp bản đồ OpenStreetMap (vẫn dùng online tile cho nền trực quan)
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Mảng chứa các điểm đánh dấu (markers) trên bản đồ
let danhSachDiemDanhDau = [];
// Biến giữ đối tượng đường đi (polyline) vẽ trên bản đồ
let duongDanVe;

// Hàm vẽ đường đi trên bản đồ
function veDuongDi(duongDi) {
  // Nếu đã có đường đi trước đó, xóa nó đi
  if (duongDanVe) map.removeLayer(duongDanVe);

  if (duongDi && duongDi.length > 0) {
      // Tạo đường polyline mới từ dữ liệu đường đi và thêm vào bản đồ
      console.log("Dữ liệu đường đi:", duongDi); // Log để kiểm tra dữ liệu đường đi
      duongDanVe = L.polyline(duongDi, { color: 'blue' }).addTo(map);
      // Căn chỉnh bản đồ để hiển thị toàn bộ đường đi
      // Kiểm tra bounds hợp lệ trước khi fit
      if (duongDanVe.getBounds().isValid()) {
        map.fitBounds(duongDanVe.getBounds(), {
            maxZoom: 16, // Giới hạn mức zoom tối đa khi hiển thị đường đi
            padding: [50, 50] // Thêm khoảng cách xung quanh đường đi
        });
      }
  } else {
      console.warn("Không có dữ liệu đường đi để vẽ.");
  }
}

// map.setMaxBounds([
//     [10.843548, 106.785414], // Góc Tây Nam (South-West)
//     [10.850661, 106.798139]  // Góc Đông Bắc (North-East)
// ]);

// Hàm thêm một điểm đánh dấu vào bản đồ
function themDiemDanhDau(toaDo, nhan) {
  const diemDanhDau = L.marker(toaDo).addTo(map).bindPopup(nhan).openPopup();
  // Thêm điểm đánh dấu vào danh sách
  danhSachDiemDanhDau.push(diemDanhDau);
}

// --- Lấy ranh giới từ server và thiết lập bản đồ ---
$.getJSON('/bounds', function(data) {
    if (data && data.bounds) {
        const bounds = data.bounds; // Ranh giới nhận được từ server
        // console.log("Ranh giới từ server:", bounds); // Log để kiểm tra


        // Thiết lập chế độ xem ban đầu vừa với ranh giới
        map.fitBounds([
            [bounds[0], bounds[1]], // Góc Tây Nam (South-West)
            [bounds[2], bounds[3]]  // Góc Đông Bắc (North-East)
        ]);
        // Tùy chọn: Giới hạn khả năng di chuyển/phóng to của người dùng trong ranh giới này
        // map.setMaxBounds(bounds); // Bỏ comment nếu bạn muốn giới hạn nghiêm ngặt
    } else {
        console.error("Không nhận được ranh giới từ server hoặc dữ liệu không hợp lệ.");
        // Nếu không lấy được bounds, setView về một vị trí mặc định
        map.setView([10.762622, 106.660172], 17);
    }
}).fail(function(jqxhr, textStatus, error) {
    const err = textStatus + ", " + error;
    console.error("Đã xảy ra lỗi khi lấy ranh giới từ server: " + err);
    // Nếu gọi API lỗi, setView về một vị trí mặc định
    map.setView([10.762622, 106.660172], 17);
});
// --------------------------------------------------


// Lắng nghe sự kiện click trên bản đồ
map.on('click', function(e) {
  // Nếu đã có 2 điểm đánh dấu, xóa tất cả để bắt đầu lại
  if (danhSachDiemDanhDau.length >= 2) {
    danhSachDiemDanhDau.forEach(diem => map.removeLayer(diem));
    if (duongDanVe) map.removeLayer(duongDanVe);
    duongDanVe = null; // Reset biến duongDanVe
    danhSachDiemDanhDau = [];
    // Xóa nội dung trong ô input khi làm mới
    $('#startPoint').val('');
    $('#endPoint').val('');
  }

  // Lấy tọa độ từ sự kiện click
  const toaDoClick = [e.latlng.lat, e.latlng.lng];
  // Định dạng tọa độ làm tròn 6 chữ số thập phân
  const toaDoString = `${toaDoClick[0].toFixed(6)}, ${toaDoClick[1].toFixed(6)}`;

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
    // Tạo URL để gọi API tìm đường
    const url = `/route?orig_lat=${diemBatDau.lat}&orig_lon=${diemBatDau.lng}&dest_lat=${diemKetThuc.lat}&dest_lon=${diemKetThuc.lng}`;

    // Gửi yêu cầu GET đến server để lấy dữ liệu đường đi
    $.getJSON(url, function(duLieu) {
        if (duLieu && duLieu.route && duLieu.route.length > 0) {
            veDuongDi(duLieu.route); // Vẽ đường đi trên bản đồ
        } else if (duLieu && duLieu.error) {
            console.warn(duLieu.error);
            alert(duLieu.error); // Hiển thị lỗi từ server
        } else {
            console.warn("API route không trả về dữ liệu đường đi hợp lệ.");
            alert("Không tìm thấy đường đi giữa hai điểm này.");
        }
    }).fail(function(jqxhr, textStatus, error) {
        console.error("Đã xảy ra lỗi khi gọi API route:", textStatus, error);
        alert("Đã xảy ra lỗi khi tìm đường đi. Vui lòng kiểm tra console log.");
    });
  }
});
// Trình lắng nghe sự kiện cho nút "Chọn trên bản đồ"
$('#selectOnMapButton').on('click', function() {
    alert('Bây giờ hãy click vào bản đồ để chọn điểm Xuất phát (click lần 1) và Đích đến (click lần 2).');
    // Có thể thêm logic để cuộn xuống bản đồ nếu cần
    map.invalidateSize(); // Cập nhật kích thước bản đồ nếu nó bị ẩn ban đầu
});

// Quan trọng: Gọi invalidateSize() sau khi đảm bảo div bản đồ đã hiển thị và có kích thước.
// Điều này khắc phục sự cố hiển thị bản đồ (chỉ hiển thị một phần nhỏ)
// khi nó nằm trong một layout phức tạp hoặc ban đầu bị ẩn.
// Gọi sau khi đã cố gắng setView/fitBounds ban đầu
$(window).on('load', function() {
    map.invalidateSize();
});
