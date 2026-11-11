# Đối chiếu thiết kế và source — 10/11/2026

Nguồn: `tieuluan_V4_03_07_HungNM_040.pdf` (86 trang), `design-phase-entity-class-diagram.vpp`, `design-phase-entity-relationship-diagram.vpp`, `3-layer-diagram.vpp` trong `TieuLuan/tl-VPP-diagrams`. Đọc VPP bằng SQLite mode read-only; không thay đổi PDF/VPP.

## Quyết định khi tài liệu chưa thống nhất

- UUID ở entity được lưu TEXT 36 ký tự, trả chuỗi qua API. Bản ghi mới dùng UUID4; ID số cũ được ánh xạ UUID5 xác định theo tên bảng và ID gốc để giữ toàn bộ FK. URL/body chứa ID số nguyên không còn là hợp đồng API mới.
- Product.status theo class String: `ACTIVE` hoặc `ARCHIVED`; không dùng Boolean của ERD. API `published` là cờ suy ra để giao diện cũ tiếp tục hoạt động. Mọi truy vấn mua hàng kiểm tra bản ghi hiện hành.
- Tiền dùng integer VND xuyên suốt, không float, đúng quy ước thuật toán chương 5. SQLite INTEGER lưu 64 bit; input giá cho phép tới 10^12 VND. Đây là ánh xạ scale 0 của DECIMAL trong ERD; chưa hỗ trợ tiền lẻ/ngoại tệ.
- Giữ khách vãng lai theo FR03/FR04/FR08: Cart có owner phiên riêng và customer_id nullable cho khách. Mỗi tài khoản có một Cart với customer_id UNIQUE. SearchQuery của khách lưu guest_owner thay cho customer_id. Không tạo tài khoản giả. Đây là phần bổ sung có chủ đích cho các FK bắt buộc của ERD, như PDF mục 4.2.2 đã xác định.
- Danh mục duyệt chính là sáu loại Product. Bỏ bảng categories, products.category_id và CRUD danh mục cha/con. API `/api/product-types` trả sáu mã ổn định cùng nhãn/trường nhập từ `shared/product_types.py`; menu, bộ lọc và form quản trị cùng dùng dữ liệu này. Book.category vẫn là thể loại sách trong bảng book. Không tạo ProductSize. Không quy đổi tồn kho giữa cây/hộp.
- Giữ vận chuyển, hỗ trợ, lịch sử, audit và bổ sung hàng theo FR09–FR25. Các bảng này là phần vận hành ngoài phạm vi ERD lõi, không xóa chỉ vì không được vẽ.

## Ánh xạ lưu trữ

Giữ tên bảng/khóa API của source đang có thay vì đổi đồng loạt tên SQL. Ánh xạ entity/ERD → implementation:

| Thiết kế | Bảng source | Cột/luật |
|---|---|---|
| Customer | users | id = customerId; name = full_name; password chứa hash = password_hash; active; phone/role bổ sung cho vận hành |
| Product | products | id = product_id; stock = stockQuantity; selling_unit = sellingUnit; origin, material, average_rating, created_at, updated_at |
| Pen…ElectricDevice | pen, notebook, bag, toy, book, electric_device | product_id PK/FK chung; trường bắt buộc và nullable theo ERD; không có ID riêng |
| ProductImage | product_image | id = image_id; một ảnh chính mỗi Product; encoder_version/vector_reference cho phép chưa có |
| Cart | carts | UUID id; customer_id UNIQUE; status EMPTY/HAS_ITEMS do trigger cập nhật |
| CartItem | cart_items | UUID id, cart_id, product_id, quantity, unit_price; UNIQUE(cart_id,product_id) |
| Order | orders | id = order_id; user_id = customer_id; address = shipping_address; total = total_amount; chụp thông tin giao hàng |
| OrderItem | order_items | UUID id; name = product_name_snapshot; price = unit_price; snapshot đơn vị bán và thông số bổ sung |
| Payment | payments | UUID id riêng; order_id UNIQUE; COD/ONLINE; PENDING/PROCESSING/PAID/FAILED/REFUNDED; reference = transaction_code |
| Review | reviews | UUID id; user_id = customer_id; một review/khách/sản phẩm, điểm 1–5, mua và giao thành công |
| SearchQuery/Filter/Result/QueryMedia | search_query, search_filter, search_result, query_media | UUID, bản số FK, modality, filter, rank, scores và media reference theo ERD |

`product_type` là discriminator của sáu bảng chuyên biệt. SQL trigger chặn INSERT vào bảng con không đúng loại Product; CatalogService cập nhật bảng con trong cùng transaction. Form mới buộc chọn loại và validate trường tương ứng. Dữ liệu văn phòng phẩm cũ ngoài sáu loại không tự gán nhãn sai: giữ Product với product_type NULL và status ARCHIVED, hiển thị “Cần phân loại” trong quản trị; chưa được xuất bản cho tới khi chọn loại và điền đủ trường tương ứng. Dữ liệu JSON bổ sung cũ được giữ để không mất thông số, không thay cho sáu bảng con.

`pack_quantity` không còn là cột Product hay OrderItem. Số chiếc trong đơn vị của dữ liệu cũ được giữ trong metadata JSON và snapshot đơn; selling_unit ở Product, không lặp lại ở Pen. `reserved` không còn là cột Product: inventory_reservations giữ số lượng theo Order/Product. Trường API reserved/available được tính từ tổng reservation; CHECK/trigger và BEGIN IMMEDIATE chặn âm kho/bán vượt tồn. Giao hàng trừ stock sau khi xóa reservation tương ứng; hủy/thất bại giải phóng reservation.

## Trách nhiệm ba tầng

- CatalogService: `application/catalog_service.py`, Product và sáu subtype, ảnh, trạng thái bán, xuất xứ/chất liệu.
- ReviewService: `application/review_service.py`; ProductController nhận đánh giá và gọi service. Sau INSERT review thành công cập nhật Product.average_rating trong cùng transaction.
- Theo yêu cầu cập nhật ngày 11/11/2026, bỏ mã giảm giá khỏi giao diện, quản trị, API và báo cáo. CheckoutService chỉ tính tiền hàng và phí giao hàng. Bảng promotions và cột promo/discount cũ được giữ để tương thích migration và bảo toàn đơn lịch sử; đơn mới luôn lưu promo rỗng và discount = 0.
- OrderService gọi InventoryService và PaymentService; các service tham gia cùng transaction tạo đơn trước thanh toán. Một Payment hiện hành mỗi Order, sự kiện demo idempotent riêng.
- HTTP/session/CSRF/role ở Presentation. Application không import Flask hoặc controller. Infrastructure không import Application.
- Không thêm class bọc tương ứng mỗi component; module/function theo mục 5.1 của PDF.

## Phiên đăng nhập

Customer không có sessionVer/session_version. Cookie chỉ giữ user_id và token phiên ngẫu nhiên; bảng auth_sessions lưu SHA-256 của token, không lưu token nguyên bản. Đổi mật khẩu xóa các phiên cũ và cấp lại phiên hiện tại. Reset mật khẩu hoặc khóa tài khoản xóa các phiên; mở khóa không làm sống lại cookie cũ. Recovery token vẫn dùng một lần, có hạn 15 phút. Không đưa token vào JSON gửi cho frontend.

## Tìm kiếm và media

- Keyword/VOICE ghi query, các filter áp dụng và thứ hạng trả về. Không tự nới filter explicit; không dùng preference cá nhân chưa được xác nhận.
- Voice chỉ điền transcript; khách kiểm tra/sửa rồi bấm tìm. Không lưu âm thanh.
- Ảnh được validate định dạng, dung lượng và pixel, re-encode RGB PNG để không giữ EXIF; lưu trong thư mục riêng cạnh DB, không phục vụ qua assets. QueryMedia ghi tham chiếu, MIME, kích thước, hạn 24 giờ.
- Log query quá 24 giờ được xóa khi có tìm kiếm tiếp theo; ảnh hết hạn được dọn khi có tìm ảnh tiếp theo. Đây là dọn theo truy cập, không phải cam kết xóa đúng giây khi server không chạy. Có thể đặt QUERY_MEDIA_DIRECTORY riêng.
- KeywordIndex/VectorIndex luôn lấy catalogue đang ACTIVE, giá và available hiện hành. ImageEmbeddingAdapter vẫn là baseline màu/bố cục như PDF chương 5. Text search có lựa chọn keyword/semantic với TextEmbeddingAdapter local; xem [semantic-text-search.md](semantic-text-search.md).

## Nâng cấp dữ liệu

`init_db` kiểm tra PRAGMA user_version. Database v1 được backup sang `<DATABASE>.pre-design-v2.sqlite` trước khi đổi UUID/cart/payment. Database v2 tiếp tục được backup sang `<DATABASE>.pre-design-v3.sqlite` trước khi bỏ Category. Hai bước giữ toàn bộ ID/FK, đơn, giỏ, tồn kho và snapshot; lỗi rollback bước hiện tại. Phiên bản mới hơn app bị từ chối thay vì bị hạ cấp. Dừng app cũ trước khi khởi động bản mới.

Migration v3 giữ danh mục và ánh xạ sản phẩm cũ trong migration_archive (JSON chỉ phục vụ đối chiếu), rồi loại bảng categories và cột category_id khỏi schema hoạt động. Các Product chưa có loại chuyển ARCHIVED, không xóa. Snapshot backup giữ cả trạng thái và danh mục trước nâng cấp. Migration thành công không chạy lại khi mở app lần sau.

Đã thử trên bản sao DB runtime v2: giữ 5 users, 12 products, 1 order, 1 order item, 1 cart item và 0 reviews; integrity OK, không lỗi FK. Trong dữ liệu này có 8 Product chưa phân loại được chuyển sang lưu trữ, 4 Product đã có loại vẫn đang bán. Không sửa DB runtime gốc trong lượt kiểm tra; lần restart app sẽ tự nâng cấp.

## Xác minh

- 55 pytest passed, gồm kiến trúc, sáu subtype, loại sản phẩm thay Category, migration v1/v2 → v3, bảo toàn dữ liệu và rollback.
- Production React build passed.
- 14 Playwright desktop/mobile Edge passed: browse/filter/detail, guest merge, checkout/payment, voice confirmation/image search, admin catalogue/inventory/report và role/support; kiểm tra menu/footer/bộ lọc sáu loại và tạo đủ sáu loại qua form.
- Test migration bao gồm bản có dữ liệu và rollback khi dữ liệu cũ có FK hỏng. Các kiểm thử dùng DB riêng.

Chưa kiểm thử provider thanh toán/vận chuyển thật, micro thật hoặc chất lượng semantic AI; không triển khai production. Hai file VPP vẫn có các khác biệt status, currency và ownership nêu trên, không coi chúng là schema SQL hoàn chỉnh để generate trực tiếp.
