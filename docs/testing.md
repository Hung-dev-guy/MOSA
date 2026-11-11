# Kế hoạch kiểm thử tự động Mosa

## Cập nhật 10/11/2026

Thêm `tests/test_design_alignment.py`: sáu subtype dùng PK/FK chung, UUID, CartStatus, tìm kiếm/media, session không version, migration có backup và rollback. Bộ đầy đủ hiện có 55 pytest và 14 Playwright; xem `test-evidence.md`.

## 1. Quy trình bắt buộc
Thiết kế bốn file docs trước coding. Mỗi feature hoàn thành phải chạy nhóm pytest tương ứng; chỉ tiếp tục sau pass. Cuối cùng chạy pytest toàn bộ, frontend build và Playwright E2E. Kết quả thực tế lưu docs/test-evidence.md; case chưa chạy phải ghi Not run, không suy ra Pass từ kế hoạch.

Sau khi chia folder theo `3-layer-diagram.vpp`, chạy thêm `tests/test_architecture.py`: Application không phụ thuộc HTTP/Presentation, Infrastructure không phụ thuộc lớp trên, controller không chứa SQL và mỗi API/method chỉ đăng ký một lần. Các integration/E2E hiện có giữ nguyên expected behavior khi chuyển module.

## 2. Nhóm kiểm thử và expected outcomes
| Group | UC / FR | Scenarios |
|---|---|---|
| identity | UC01,15 / FR01,NFR04 | đăng ký, duplicate email, sai password, CSRF, role denial, block active session, logout/cart isolation, profile, đổi mật khẩu, recovery token expiry/one-time/revoke sessions |
| discovery | UC02,03,13,20,21,22 / FR02–05,15 | published only, product_type/brand/price/attribute filters kết hợp, accent-insensitive search, sorting/pagination, missing product, image decode/type/size errors, search không đổi stock/cart/order, voice unsupported/denied fallback |
| cart | UC04 / FR08 | visitor persistent session, merge same id, separate pack id, invalid fractional/negative quantity, update/remove, login merge, user isolation |
| orders | UC05,06,19 / FR06–12,14,22 | order before payment, atomic reservation, overstock rollback, changed price 409, idempotency/mismatched payload, pending/failed/success, duplicate event, terminal event ignored, failed retry reserve, no oversell concurrent clients, snapshots, ownership, cancel, notification |
| operations | UC07–10,14–18 / FR02,09,15–17,19–25 | publication validation, six product types, discount codes rejected and promotion routes removed, stock receipt and adjustment integrity, warehouse role, fulfilment transitions/stock deduction once, COD collection on delivery, shipment dedupe, supply receive once, support/exceptions/audit, privacy views |
| reports_reviews | UC11,12 / FR13,18 | delivered-only rating, 1–5/duplicate review, paid-only sales, UTC period validation/filter, service metrics, inventory available, CSV |
| recovery | NFR06,07 | DB reopen durability, backup/restore integrity, schema constraints |

Bổ sung test_product_types.py: không còn Category storage/CRUD; lọc từng loại; đổi subtype; migration v2 có lưu trữ ánh xạ cũ, rollback DDL và chống downgrade. E2E thêm duyệt sáu loại qua menu/footer/chips và tạo đủ sáu subtype qua form, trên cả desktop và mobile.

## 3. Commands
```powershell
.\.venv\Scripts\python -m pytest tests/test_identity.py -q
.\.venv\Scripts\python -m pytest tests/test_discovery.py -q
.\.venv\Scripts\python -m pytest tests/test_cart.py -q
.\.venv\Scripts\python -m pytest tests/test_orders.py -q
.\.venv\Scripts\python -m pytest tests/test_operations.py tests/test_reports_reviews.py -q
.\.venv\Scripts\python -m pytest -q --junitxml=docs/pytest-results.xml
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```
Tests dùng temporary SQLite, fixed seed, independent client và stable fixture; không xoá data runtime. E2E tạo database riêng bằng scripts/e2e_server.py, webServer setup/teardown tự động.

## 4. Browser acceptance
Desktop 1440px và mobile 390px: catalogue, filter, product details, cart, account registration, quote, checkout demo pending/success, order timeline, staff workflow. Verify errors, empty results, keyboard labels, no horizontal document overflow. Screenshot lưu docs/evidence. Browser speech dùng test stub chỉ kiểm tra wiring/fallback, không claim đã nhận dạng microphone thật. Image rank test baseline dùng catalogue image/query fixture; không phải benchmark semantic AI.

## 5. Không thể chứng nhận bằng suite local
Provider thật, email thực, speech recognition dịch vụ, AI relevance dataset, 99.5% uptime, TLS, mã hoá ổ đĩa, production load profile và RPO/RTO chưa xác định. Ghi giới hạn rõ ở evidence và README. Không tự thêm hoàn tiền tự động.
