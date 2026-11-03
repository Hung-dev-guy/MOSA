# MOSA Stationery — Multimodal Product Search

Website văn phòng phẩm chạy cục bộ, lấy cảm hứng từ nhịp bố cục của ADCBook nhưng dùng nhận diện, nội dung và mã nguồn riêng. Ứng dụng hỗ trợ tìm sản phẩm bằng văn bản, giọng nói hoặc hình ảnh và có thể chạy trọn bộ bằng Docker Compose.

## Tính năng

- Tìm kiếm tiếng Việt bằng text và xếp hạng theo tên, mô tả, thương hiệu, danh mục, màu sắc.
- Tìm kiếm bằng giọng nói `vi-VN` qua Web Speech API.
- Tìm kiếm bằng ảnh dựa trên màu chủ đạo, có thể thay encoder bằng CLIP sau này.
- Giao diện responsive cho máy tính và điện thoại.
- Catalog có 101 sản phẩm, trong đó 89 sản phẩm đang hoạt động và 50 sản phẩm còn hàng.
- 89 ảnh catalog thật được đóng gói cùng source.
- Ghi lịch sử truy vấn vào `dbo.SearchEvents`.
- Không sử dụng bảng `ProductSize`.

## Kiến trúc

```text
Presentation (Flask routes + responsive web UI)
                    │
Application (SearchOrchestrator + RankingService + ImageEncoder)
                    │
Infrastructure (ProductRepository + pyodbc + SQL Server)
```

- Text: chuẩn hóa tiếng Việt, khớp tên/mô tả/brand/category/color và xếp hạng.
- Voice: Web Speech API (`vi-VN`) chuyển giọng nói thành text rồi dùng cùng pipeline.
- Image: encoder local lấy màu chủ đạo từ ảnh, kết hợp mô tả tùy chọn và xếp hạng catalog. `DominantColorImageEncoder` là điểm thay thế trực tiếp bằng CLIP + vector index sau này.
- Mỗi lần tìm được ghi vào `dbo.SearchEvents` bằng truy vấn tham số hóa.
- Không sử dụng bảng `ProductSize`. Migration `database/001_remove_product_size.sql` chỉ xóa nếu bảng tồn tại.
- Catalog văn phòng phẩm và giá VND ban đầu được thiết lập bởi `database/002_stationery_catalog.sql`.
- Trước khi đổi catalog, migration local lưu bản ghi cũ trong schema `archive` để có thể khôi phục.
- Dữ liệu nguồn được đưa vào `dbo.ExternalProductStaging`, tách khỏi catalog đang bán để không biến trạng thái “hết hàng” thành tồn kho giả.
- Catalog Docker hiện có 101 bản ghi `Products`, 89 bản ghi staging và 89 sản phẩm active.
- SKU hết hàng giữ `Stock=0`; hệ thống không tự tạo tồn kho giả.

## Hướng dẫn nhanh cho người nhận dự án

### 1. Yêu cầu

- Windows 10/11, macOS hoặc Linux có Docker Desktop/Docker Engine.
- Docker Compose v2.
- Tối thiểu khoảng 4 GB RAM trống cho SQL Server và website.

Bạn không cần cài Python, SQL Server hoặc ODBC Driver riêng nếu chạy bằng Docker.

### 2. Clone repository

Sao chép URL tại nút **Code** trên GitHub, sau đó chạy:

```powershell
git clone <URL-repository>
cd multimodal-store
```

Nếu repository đang private, chủ repository phải thêm tài khoản GitHub của bạn vào danh sách collaborator trước.

### 3. Khởi động

Mở Docker Desktop, chờ engine báo đang chạy rồi thực hiện:

```powershell
.\start-docker.ps1
```

Lần đầu Docker sẽ tải image SQL Server và build image Flask nên có thể mất vài phút. Script tự:

1. Tạo mật khẩu SQL Server riêng trong `.env.docker`.
2. Khởi động SQL Server 2022.
3. Tạo database `ECommerceMultimodalV1`.
4. Nạp 101 sản phẩm và 89 bản ghi staging.
5. Khởi động website bằng Gunicorn.

Khi hoàn tất, mở:

```text
http://localhost:5050
```

Kiểm tra database và website:

```powershell
docker compose --env-file .env.docker ps
```

Các service `db` và `web` phải có trạng thái `healthy`; `db-init` kết thúc với mã `0` là bình thường.

### 4. Dừng và chạy lại

Dừng container nhưng giữ database:

```powershell
.\stop-docker.ps1
```

Chạy lại:

```powershell
.\start-docker.ps1
```

Database nằm trong Docker Volume nên không bị mất khi chỉ chạy `down`.

### 5. Xử lý lỗi thường gặp

Nếu cổng 5050 hoặc 14330 đang được sử dụng, sửa `.env.docker`:

```env
APP_PORT=5051
SQL_PORT=14331
```

Sau đó mở website tại cổng `APP_PORT` mới.

Nếu Docker báo `overlayfs ... read-only file system`, hãy khởi động lại Docker Desktop hoặc khởi động lại máy rồi thử lại. Đây là lỗi storage của Docker Desktop, không phải lỗi SQL seed.

Xem log khi cần:

```powershell
docker compose --env-file .env.docker logs --tail 100 db
docker compose --env-file .env.docker logs --tail 100 db-init
docker compose --env-file .env.docker logs --tail 100 web
```

Xóa toàn bộ database Docker và tạo lại từ seed:

```powershell
docker compose --env-file .env.docker down --volumes
.\start-docker.ps1
```

## Chạy trực tiếp không dùng Docker

Yêu cầu: SQL Server đang chạy, Windows Authentication truy cập được `localhost/ECommerceMultimodalV1`, Python 3.11+ và ODBC Driver 18.

```powershell
cd C:\Users\lekim\OneDrive\Documents\ChatGPT\PTTKHTTT\multimodal-store
.\run.ps1
```

Mở <http://127.0.0.1:5050>. Lần chạy đầu script tạo `.venv` và cài các dependency trong `requirements.txt`.

Các biến cấu hình tùy chọn có trong `.env.example`; đặt chúng ở môi trường PowerShell trước khi chạy nếu instance/database khác mặc định.

## Cấu trúc Docker

```text
docker-compose.yml
├── db       — SQL Server 2022 Developer + persistent volume
├── db-init  — tạo schema và seed dữ liệu
└── web      — Flask + Gunicorn + ODBC Driver 18
```

- `database/docker/001_schema.sql`: schema có thể chạy lặp lại.
- `database/docker/002_seed_data.sql`: dữ liệu demo có thể chạy lặp lại mà không nhân đôi.
- `tools/init_database.py`: chờ SQL Server, chạy schema/seed và kiểm tra số bản ghi.
- `tools/export_docker_database.py`: xuất lại seed từ SQL Server local.
- `start-docker.ps1`: tự sinh secret và khởi động hệ thống.
- `package-docker.ps1`: tạo gói ZIP sạch để gửi.

## Bảo mật và bản quyền dữ liệu

Không commit `.env`, `.env.docker`, mật khẩu SQL Server hoặc access token. Khi triển khai thật, sử dụng secret manager, HTTPS và xác thực người dùng.

Ảnh sản phẩm ADCBook/Bizweb trong repository chỉ phục vụ prototype/đồ án nội bộ. Cần xin phép chủ sở hữu trước khi phân phối lại hoặc sử dụng thương mại.

## Chi tiết vận hành Docker

Gói Docker gồm ba service:

- `db`: SQL Server 2022 Developer với volume lưu dữ liệu.
- `db-init`: tạo schema và nạp 101 sản phẩm cùng 89 bản ghi nguồn staging.
- `web`: Flask chạy bằng Gunicorn tại cổng 5050.

Trong PowerShell tại thư mục dự án:

```powershell
.\start-docker.ps1
```

Script tự sinh mật khẩu SQL Server mạnh trong `.env.docker`. File này đã được `.gitignore` và không được đưa vào gói ZIP. Khi các container đã healthy, mở <http://localhost:5050>.

Dừng hệ thống nhưng giữ database:

```powershell
.\stop-docker.ps1
```

Xóa cả container và database Docker để làm lại từ đầu:

```powershell
docker compose --env-file .env.docker down --volumes
```

Nếu cổng 5050 hoặc 14330 đã được dùng, sửa `APP_PORT` hoặc `SQL_PORT` trong `.env.docker` rồi khởi động lại.

### Tạo file ZIP để gửi

```powershell
.\package-docker.ps1
```

File `output/MOSA-Stationery-Docker.zip` chứa source, ảnh catalog thật, Docker Compose và dữ liệu demo. Nó không chứa `.venv`, mật khẩu, lịch sử tìm kiếm, thư mục dataset thô hoặc file debug.

### Làm mới dữ liệu seed

Sau khi chỉnh catalog trong SQL Server local, xuất lại schema và dữ liệu Docker bằng:

```powershell
.\.venv\Scripts\python.exe tools\export_docker_database.py
```

Sau đó chạy lại `package-docker.ps1`.

