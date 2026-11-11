# Xác minh semantic text search — 11/11/2026

- 78 pytest passed, toàn bộ backend/architecture, 48.65 giây.
- 20 Playwright passed desktop/mobile Edge, 54.0 giây; bao gồm semantic search với model local thật và lỗi dịch vụ giả lập.
- Production React build passed; `pip check` không có dependency conflict.
- Đã tải và chạy multilingual MiniLM ONNX, 384 chiều; probe tiếng Việt kiểm tra khác biệt keyword/semantic và truy vấn ngoài catalogue.
- Chưa có bộ nhãn để đo Precision@k/Recall@k; ngưỡng cosine 0.35 là ngưỡng demo, chưa bảo đảm chất lượng ngữ nghĩa tổng quát. Xem [semantic-text-search.md](semantic-text-search.md).

## Xác minh cập nhật thiết kế — 10/11/2026

- 55 pytest passed (0 failed/skipped), `docs/pytest-results.xml`.
- Production React build passed.
- 14 Playwright passed desktop/mobile Edge, `docs/playwright-results.json`.
- Bản sao DB runtime migration giữ 5 users / 12 products / 1 order / 1 order item / 1 cart item / 0 reviews; integrity OK, 0 FK errors. Không sửa DB runtime gốc; bản sao đã bỏ Category/cột category_id, chuyển 8 Product chưa có loại sang lưu trữ.
- 11 test mới kiểm tra sáu subtype, UUID/CartStatus, lưu tìm kiếm/ảnh, session không version, migration/backup và rollback.

Hai bài E2E mới (mỗi bài chạy desktop/mobile) kiểm tra sáu loại trên menu/footer/bộ lọc và tạo đủ sáu subtype qua UI. Test v3 kiểm tra schema không còn Category, FK/dữ liệu còn nguyên, backup và rollback cả DDL.

Chi tiết ánh xạ và giới hạn ở [design-alignment.md](design-alignment.md). Voice dùng stub; payment/shipping demo/nhập tay, chưa kiểm tra tích hợp thật hoặc semantic AI.

---

## Biên bản cũ (05/11/2026)

# Biên bản kiểm thử Mosa

## Môi trường
Ngày 05/11/2026, Asia/Bangkok. Windows, Python 3.14.7, Flask 3.1.3, Pillow 12.3.0, pytest 9.2.0; Node 24.20.0, npm 11.19.0, React 19.3.1, Vite 7.3.7, Playwright 1.64.1. Bộ test browser dùng Edge có sẵn, headless, một worker. Không tạo commit; kết quả áp dụng cho working tree cuối của lượt triển khai này.

## Quy trình đã thực hiện
Đã xoá cấu trúc cũ và Docker theo yêu cầu, giữ `.git`. Đọc chương 1–4 qua OOXML, kiểm tra trực tiếp bảng MODEL_ELEMENT/DIAGRAM trong các file SQLite VPP bằng mode read-only; inventory ở vpp-inventory.json. Không sửa tài liệu nguồn hoặc VPP. Đã tạo architecture, UI design, API definition, testing trước code.

Mỗi nhóm backend được chạy và pass trước khi tiếp tục nhóm kế tiếp:

| Lệnh nhóm | Kết quả |
|---|---|
| pytest tests/test_identity.py -q | 5 passed |
| pytest tests/test_discovery.py -q | 3 passed |
| pytest tests/test_cart.py -q | 3 passed |
| pytest tests/test_orders.py -q | 6 passed |
| pytest tests/test_operations.py tests/test_reports_reviews.py -q | 8 passed |

Thêm test backup/restore và production serving sau khi tích hợp; sau đó chạy toàn bộ backend và browser.

## Kết quả cuối

| Check | Kết quả | Bằng chứng |
|---|---|---|
| `.venv/Scripts/python -m pytest -q --tb=short --junitxml=docs/pytest-results.xml` | 31 passed, 0 failed, 0 skipped | pytest-results.xml |
| `npm --prefix frontend run build` | Passed, 1598 modules, JS khoảng 331 kB / gzip 102 kB | build output |
| `npm --prefix frontend run test:e2e` | 10 passed, 0 failed/skipped/flaky | playwright-results.json |
| `git diff --check` | Passed; chỉ cảnh báo chuyển LF/CRLF từ Git | terminal output |

27 test nghiệp vụ gồm authentication/CSRF/recovery/ownership, public discovery/combined filters/image validation, cart/session merge, checkout/reservation/idempotency/payment snapshots, concurrency no-oversell, RBAC/customer block, catalogue/category cycle, promotions, stock/supply, fulfilment/shipping event dedupe, support/audit, delivered review, period reports/CSV, DB constraints và backup restore. Serving test kiểm tra JS/CSS production không bị route ảnh che. Sau refactor bổ sung 4 test kiến trúc, tổng 31 test.

Lượt xác minh sau refactor 3 lớp ngày 05/11/2026 khoảng 02:02–02:03 Asia/Bangkok: 31 pytest pass (14,52 giây), 10 E2E pass (25,8 giây), build React pass. Controller và service đã tách thật; Application không còn Flask/HTTP/session. Data Infrastructure không phụ thuộc lớp trên; controller không chứa SQL; route không đăng ký trùng. CustomerUI/AdminStaffUI đã tách và bỏ vòng import từ staff về main. Database schema, runtime path và hợp đồng API giữ nguyên; không chuyển hoặc xoá dữ liệu instance.

10 E2E = 5 scenario × 2 viewport:
1. Catalogue, keyword không dấu, brand + giá, empty, detail và không tràn viewport.
2. Guest cart → register → quote lỗi/ưu đãi hợp lệ → checkout → demo payment → own order.
3. Voice unsupported + mocked transcript, upload ảnh và baseline ranking.
4. Admin sửa catalogue, nhập kho, xem báo cáo và download CSV.
5. Warehouse thấy tab đúng quyền và gửi support enquiry.

Desktop 1440×1000; mobile 390×664, deviceScaleFactor 3/touch. Mobile chạy Edge/Chromium với mô phỏng iPhone viewport, **không phải Safari thật**. Test database riêng tại .test-runtime, không dùng dữ liệu runtime instance.

## Lỗi phát hiện và sửa
- Windows sandbox chặn tải package và esbuild đọc thư mục cha: cài/build qua execution được cấp quyền, không sửa policy hay thư mục ngoài workspace.
- Pytest temp mặc định bị giới hạn truy cập: chuyển basetemp vào workspace .test-tmp.
- Route /assets ban đầu chỉ trả ảnh, làm bundle JS/CSS production 404: thêm ưu tiên dist/assets và regression test.
- Nhãn implicit của select bị tính cả text options trong locator: Field dùng aria-labelledby với useId; test admin desktop/mobile pass sau sửa.
- Image search có thể bỏ qua bộ lọc: dùng chung catalogue filtering trước ranking, thêm assertion category.
- Screenshot full-page có lazy images chưa tải: test cuộn và chờ decode trước chụp trang chủ. Đã xem screenshot desktop/mobile trang chủ, đơn hàng và báo cáo; không thấy overflow tài liệu, giá và thao tác chính đều hiện.

## Giới hạn thực tế

### Nhập ADCBook — 2026-11-10

- Đã nhập vào `instance/mosa.sqlite`: 120 SKU, 20 SKU mỗi loại trong sáu loại sản phẩm; 83 SKU có trạng thái nguồn không có sẵn. Tất cả SKU nhập có `ACTIVE` và tồn khả dụng demo 100. 18 thiết bị điện được chuẩn hóa đơn vị bán thành `Chiếc` do nguồn không ghi đơn vị.
- Đã so sánh database sau nhập với bản sao lưu trước nhập: 12 sản phẩm cũ, người dùng, đơn hàng, dòng đơn hàng, giỏ hàng, đánh giá và reservation không thay đổi. `integrity_check=ok`, không có lỗi foreign key.
- Kiểm tra từng SKU qua API chi tiết và route ảnh: đủ 120/120, ảnh trả MIME image, chỉ một bảng con đúng loại và một ảnh chính/SKU.
- 67 pytest pass (gồm 12 kiểm thử importer về giá, nguồn URL, dữ liệu bắt buộc, rollback, chạy lặp và giữ đơn/reservation); frontend build pass; 14 Playwright pass trên desktop/mobile. Kiểm thử phục vụ bundle bao gồm ảnh trong thư mục con.
- Chi tiết dữ liệu/nguồn, đường dẫn backup và bản ghi bị bỏ qua: `docs/adcbook-import.json`. Dữ liệu crawl là ảnh chụp một thời điểm; tồn kho được chủ động đặt cho demo.

Không có bằng chứng cho payment/email/carrier/supplier thật, nhận dạng micro thật, AI semantic accuracy, Safari/Firefox/điện thoại vật lý, production capacity/uptime/TLS/at-rest encryption hoặc mục tiêu RPO/RTO. Image search chỉ baseline màu/bố cục; voice test kiểm tra wiring/fallback bằng stub. Refund/return ghi nhận yêu cầu để nhân viên xử lý, không tự hoàn tiền hoặc write-off stock. Các giới hạn này không được ghi thành Pass.
