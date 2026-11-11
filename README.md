# Mosa Stationery

## Chạy bằng Docker

Xem [hướng dẫn Docker](docs/docker.md) để chuẩn bị `.env`, bản sao database và model local. Sau đó chạy từ thư mục project:

```powershell
docker compose up -d --build
```

Mở http://127.0.0.1:8080. Backend Docker dùng PostgreSQL trong volume `postgres_data`; các thay đổi không ghi vào SQLite Flask local. Dừng bằng `docker compose down` (không thêm `-v` nếu muốn giữ dữ liệu).


## Chạy nhanh trên Windows

Cần Python 3.12+ và Node.js 20.19+ hoặc 22.12+.

```powershell
.\run.ps1
```

Mở [Mosa local](http://127.0.0.1:5000). Script tạo virtualenv nếu thiếu, cài thư viện Python, cài Node dependencies nếu thiếu, build React và chạy Flask. Dừng bằng Ctrl+C. Lần đầu cần mạng để cài dependencies; font web có fallback Segoe UI khi offline.

Đã cài và build trong workspace hiện tại, nên có thể chạy ngay:

```powershell
.\.venv\Scripts\python run.py
```

DB tự tạo tại `instance/mosa.sqlite`; không cần cài database server. Các lần chạy sau giữ dữ liệu.

## Tài khoản demo

Mật khẩu chung: `Mosa@12345`. Tài khoản chỉ seed khi DB chưa có user và `DEMO_MODE=1` (mặc định).

| Email | Quyền |
|---|---|
| customer@mosa.local | Mua hàng và đơn riêng |
| admin@mosa.local | Catalogue, loại sản phẩm, khách hàng, ưu đãi và toàn bộ vận hành |
| warehouse@mosa.local | Kho, bổ sung hàng và fulfilment |
| sales@mosa.local | Đơn hàng, giao hàng và hỗ trợ |
| manager@mosa.local | Báo cáo và CSV |

Đăng nhập admin rồi vào **Quản trị**. Mã `MOSA10` giảm 10% cho đơn từ 50.000đ, không cộng dồn. Phí giao hàng 25.000đ; miễn khi giá trị hàng sau ưu đãi từ 300.000đ.

## Chức năng

- Đăng ký, đăng nhập, profile, đổi mật khẩu, recovery token một lần và vô hiệu hoá tài khoản.
- Browse, keyword không dấu, bộ lọc kết hợp, sort, phân trang, detail, thông số, đơn vị bán và review.
- Tìm giọng nói bằng dịch vụ trình duyệt, có thông báo quyền và fallback; tìm ảnh PNG/JPEG/WebP qua so khớp màu và bố cục local.
- Giỏ khách vãng lai, gộp giỏ khi login, quantity, checkout quote, promotion, order snapshot và idempotency.
- Giữ kho trong transaction trước thanh toán; pending/failed/success tách biệt; retry trên cùng order, cancel đủ điều kiện, in-app notifications.
- Catalogue theo sáu loại Product, promotion/customer administration; lịch sử kho, receipt/adjustment, replenishment, picking/packing/dispatch/delivery.
- Vận đơn và tracking nhập tay có chống event trùng; support cases, ngoại lệ vận hành và audit.
- Review sau giao hàng; báo cáo kỳ UTC, doanh thu payment đã thu, tồn thực tế/đã giữ/khả dụng và CSV.

## Tài liệu thiết kế

Bốn tài liệu này được tạo trước khi code, theo cách tổ chức docs DueMate:

1. [Architecture](docs/architecture.md)
2. [UI design](docs/ui-design.md)
3. [API definition](docs/api-definition.md)
4. [Testing](docs/testing.md)

[Biên bản kiểm thử](docs/test-evidence.md), [kết quả pytest XML](docs/pytest-results.xml), [kết quả Playwright JSON](docs/playwright-results.json), [inventory sơ đồ VPP](docs/vpp-inventory.json). `source-document.txt` giữ bản trích xuất PDF hiện tại; `design-alignment.md` ghi các quyết định dung hòa chương 2, 4, 5 và sơ đồ mới.

```text
backend/
  presentation/          Sáu controller HTTP theo sơ đồ 3-layer
  application/           Các service và SearchOrchestrator
  data_infrastructure/   Database, indexes, adapters và image storage
  shared/                Validation, lỗi và project paths
  app.py                 Composition root
frontend/src/
  presentation/          CustomerUI, AdminStaffUI và UI dùng chung
  data_infrastructure/   HTTP client và SpeechRecognitionAdapter
  main.jsx               React entry point
frontend/e2e/            Playwright desktop/mobile tests
tests/         Python API/integration/concurrency/backup tests
scripts/       Test server riêng, backup và tạo ảnh minh hoạ
docs/          Thiết kế, nguồn đối chiếu và test evidence
instance/      Database runtime tự tạo, Git ignored
run.py         Entry point backend + production React bundle
run.ps1        Setup, build và chạy local
test.ps1       Chạy toàn bộ kiểm thử
```

## Kiểm thử

```powershell
.\test.ps1
```

Hoặc chạy riêng:

```powershell
.\.venv\Scripts\python -m pytest -q --junitxml=docs/pytest-results.xml
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Playwright dùng Microsoft Edge đã cài. Hai project là desktop Edge 1440×1000 và mobile viewport/touch 390×664 bằng Chromium/Edge; không phải thử Safari hoặc điện thoại vật lý. Server test port 5099 và SQLite tạm độc lập với DB runtime. Screenshots sau test nằm tại `docs/evidence/` (Git ignored). `docs/playwright-results.json` chứa thông tin môi trường tại thời điểm chạy; không có password hay token.

Kết quả sau khi chia cấu trúc theo sơ đồ 3 lớp ngày 10/11/2026: **55 pytest passed** (gồm 4 kiểm tra kiến trúc), **14 Playwright passed**, **0 failed/skipped**; frontend production build passed. Xem biên bản để biết giới hạn.

## Phát triển frontend

Terminal 1 chạy backend, terminal 2 chạy Vite:

```powershell
.\.venv\Scripts\python run.py
```

```powershell
npm --prefix frontend run dev
```

Vite proxy `/api` tới port 5000. Sau khi chỉnh React, `npm --prefix frontend run build` để bản được Flask phục vụ cập nhật.

## Backup và restore

### Dữ liệu ADCBook

Database local đã được bổ sung 120 SKU từ [ADCBook](https://adcbook.net.vn/): mỗi loại `pen`, `notebook`, `bag`, `toy`, `book`, `electric_device` có 20 SKU. Ảnh được lưu trong `frontend/public/assets/adcbook/`; chi tiết nguồn và các bản ghi bị bỏ qua nằm trong `docs/adcbook-import.json`. Chỉ nhập thông tin sản phẩm, không nhập nội dung quảng cáo. Các thiết bị điện thiếu đơn vị bán được chuẩn hóa thành `Chiếc` và ghi rõ `source_selling_unit: null` trong báo cáo.

```powershell
.\.venv\Scripts\python scripts/import_adcbook.py --per-type 20 --stock 100 --apply
```

Bỏ `--apply` để chỉ tải và kiểm tra dữ liệu. Khi áp dụng, script sao lưu database trước, dùng UUID cố định theo biến thể để không tạo trùng, giữ nguyên sản phẩm khác và đơn hàng. **100 là tồn khả dụng demo/SKU**, không phải tồn kho thực tế của ADCBook. Chạy lại sẽ đặt tồn khả dụng của các SKU nhập về 100, cộng thêm lượng đang giữ chỗ vào tồn kho tổng. Giá và dữ liệu nguồn trong cache là ảnh chụp lúc tải; script không đồng bộ theo thời gian thực.

```powershell
.\.venv\Scripts\python scripts/backup.py instance/mosa.sqlite backups/mosa-2026-11-05.sqlite
```

Destination phải chưa tồn tại. Script dùng SQLite backup API và integrity/FK check. Restore bằng cách dừng app, sao lưu DB backup sang một đường dẫn mới bằng cùng script, đặt `$env:DATABASE` trỏ tới file vừa restore rồi khởi động. Không ghi đè DB đang mở. Test đã kiểm tra dữ liệu đơn và reservation sau backup/restore; chưa chốt RPO/RTO production.

## Giới hạn tích hợp

Đây là bản local để chạy và kiểm thử đồ án. Online payment không thu tiền thật; màn hình demo cho chọn pending/success/failed. Vận chuyển và supplier là ghi nhận nội bộ/nhập tay. Recovery demo hiển thị link local, chưa gửi email. Không có hoàn tiền tự động.

Image search dùng descriptor màu/bố cục, **chưa có AI embedding/model nhận diện sản phẩm**. Kết quả tương tự không chứng minh cùng loại hoặc đơn vị bán. Voice phụ thuộc hỗ trợ và quyền micro của trình duyệt; một số browser gửi âm thanh tới dịch vụ nhận dạng của họ. Backend không giữ audio; ảnh truy vấn lưu riêng có hạn 24 giờ và dọn ảnh hết hạn khi có tìm ảnh tiếp theo. Test voice dùng stub để kiểm tra UI; chưa kiểm thử micro/dịch vụ thật.

Chưa chứng nhận uptime, tải production, TLS, mã hoá ổ đĩa, mail/provider thật hoặc mức độ liên quan AI. Secret mặc định random theo lần boot nên session sẽ hết hạn khi restart; đặt biến môi trường `SECRET_KEY` ổn định nếu muốn giữ session. `COOKIE_SECURE=1` dành cho HTTPS. Không public bản demo với seed credentials hoặc recovery demo. `DEMO_MODE=0` tắt các demo endpoint và seed demo, nhưng chưa thay thế các tích hợp production.

Tham khảo kỹ thuật: [Flask testing](https://flask.palletsprojects.com/en/stable/testing/), [Vite](https://vite.dev/guide/), [SpeechRecognition và giới hạn hỗ trợ](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition).

## Text search: từ khóa hoặc ngữ nghĩa

Thanh tìm kiếm có lựa chọn **Từ khóa / Ngữ nghĩa**, áp dụng cho văn bản nhập trực tiếp và transcript giọng nói đã xác nhận. Ngữ nghĩa chạy mô hình multilingual MiniLM local qua FastEmbed, không cần API key. Bộ lọc sản phẩm vẫn bắt buộc.

`run.ps1` cài dependencies và chuẩn bị model. Nếu chạy bằng Python trực tiếp, chuẩn bị một lần trước:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts/prepare_text_search.py
```

Lần chuẩn bị đầu cần mạng tải model (khoảng 220 MB). Các yêu cầu tìm kiếm sau chỉ dùng cache local trong `instance/text-search-model/`. Thiếu model trả thông báo và có nút chuyển sang từ khóa. Xem [semantic-text-search.md](docs/semantic-text-search.md) về API, kiểm thử và giới hạn chất lượng.


# Account
## Admin
- **Email**: quantri@mosa.local
- **Mật khẩu mới**: Mosa@12345

