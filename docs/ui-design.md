# Thiết kế giao diện Mosa

## 1. Hướng hình ảnh
Tham khảo https://adcbook.net.vn/: header tìm kiếm lớn, menu danh mục bên trái, banner ngang, dải tiện ích, product grid và giá VND nổi bật. Dùng thương hiệu Mosa từ tài liệu, không giả mạo ADCBook. Một storefront văn phòng phẩm nhiều sản phẩm, không biến thành landing page SaaS.

Palette: đỏ thương mại #c92232, đỏ đậm #a71928, nền #f5f6f8, giấy trắng #ffffff, chữ #252b36, xanh thông tin #176b59. Typography Segoe UI / Arial hỗ trợ tiếng Việt, body 15px, heading 24–34px, giá bold 19px. Nội dung căn trái; nút 44px; radius 6px cho form và 10px cho banner, card viền nhẹ không đổ shadow đồng loạt.

```text
[tiện ích / chính sách demo]
[mosa] [tìm kiếm........ mic ảnh] [tài khoản] [đơn] [giỏ]
[danh mục] [trang chủ] [sản phẩm] [hỗ trợ]
[category rail] [banner giấy bút tập vở] [gợi ý sản phẩm]
[giao hàng] [đơn vị rõ ràng] [hỗ trợ] [kiểm tra tồn kho]
[filter category brand price stock] [sort]
[product][product][product][product]
```
Review theo brief: bỏ hero trống với slogan chung; banner minh hoạ dụng cụ học tập và rail danh mục tạo trọng tâm mua sắm. Các ảnh catalogue là minh hoạ tự tạo local, không phụ thuộc hotlink.

## Cập nhật 10/11/2026

ID sản phẩm/đơn trong URL và form là UUID; bộ lọc loại dùng mã pen/notebook/bag/toy/book/electric_device. Không còn danh mục cha/con hoặc UUID Category gắn cứng. Product editor có loại sản phẩm và các trường chuyên biệt theo sáu subtype, xuất xứ/chất liệu; không yêu cầu nhập JSON. Voice cần xác nhận transcript trước tìm kiếm. Query image lưu riêng có hạn sử dụng 24 giờ, dọn theo truy cập; UI thông báo trước upload.

## 2. Màn hình và luồng
- Home/catalogue: sáu loại Product, keyword, price min/max, brand, availability, thuộc tính dạng key:value, sort, phân trang, clear filters; ảnh search ranking có nhãn giới hạn similarity.
- Detail route /product/:id: ảnh, mô tả, brand, category, specs, selling unit, pack qty, price, availability, quantity, add; review listing và review form nếu đăng nhập.
- Cart: chỉnh quantity nguyên dương, xoá, subtotal; empty có link mua hàng. Checkout: name, phone, address, payment, subtotal/shipping/total; lưu input khi lỗi; gửi idempotency key giữ nguyên khi retry mạng.
- Auth/account: login/register/profile/password/recovery/reset; error gần form; người dùng thấy role và demo status. Không dùng alert/prompt cho thao tác chính.
- Orders: lịch sử own orders, payment riêng order/shipping, timeline, snapshot, pending tracking, retry payment, cancel eligible và service request.
- Demo payment: màn hình riêng ghi rõ không thu tiền; pending/success/failure trên cùng order. Double click không tạo lại đơn.
- Staff workspace: tabs theo role. Product editor theo sáu loại; customer status; inventory receipt/adjustment + movement history; replenishment; fulfilment/shipment; support cases; audit và report period. Không hiển thị tab ngoài role.
- Reports: kỳ UTC, generated time, paid revenue không gồm COD chưa thu, counts theo trạng thái, on-hand/reserved/available, service metrics, CSV export.

## 3. Trạng thái và accessibility
Loading có text; success có feedback; empty có hướng thoát; lỗi có retry hoặc sửa form, giữ dữ liệu hợp lệ. Giá/tồn kho luôn từ server. Button pending disabled chống double submit. Labels rõ, keyboard focus visible, aria-live thông báo, modal role dialog + Escape/return focus. Không chỉ dùng màu cho payment/status.
Desktop content 1240px. <=1000px bỏ rail và đưa categories vào thanh cuộn. <=640px header wrap, grid 2 cột, form/card theo một cột; cart và staff table cuộn trong container không tràn viewport. Reduced motion tắt transition. Phải xem screenshot desktop/mobile trước bàn giao.

## 4. Phạm vi xác minh
E2E đi qua browse/detail/cart/register/checkout/payment/order và staff. Microphone thực và relevance của image baseline ghi riêng, không suy ra từ mocked browser API.
