# Chạy Mosa bằng Docker

Chạy các lệnh từ thư mục `PTTKHTTT-APP`. Docker Desktop cần ở chế độ Linux containers.

## Chuẩn bị lần đầu

Tạo `.env` với secret ngẫu nhiên (lệnh không ghi đè nếu file đã có):

```powershell
python -c "from pathlib import Path; import secrets; p=Path('.env'); p.exists() or p.write_text('MOSA_SECRET_KEY='+secrets.token_hex(32)+'\nMOSA_PORT=8080\n', encoding='utf-8')"
```

Nếu đã có `.env`, thêm `MOSA_SECRET_KEY` với giá trị ngẫu nhiên. Không commit file này.

Container web hiện kết nối PostgreSQL trong Compose. Nếu bạn đã nhập SQLite vào PostgreSQL, không nhập lại; chạy bước khởi động bên dưới. Các file SQLite cũ vẫn được giữ nguyên.

Để sao lưu SQLite trước khi chuyển dữ liệu (chỉ chạy nếu file đích chưa tồn tại):

```powershell
.\.venv\Scripts\python.exe scripts/backup.py instance/mosa.sqlite instance/mosa-before-postgres.sqlite
```

SQLite backup API tạo bản sao nhất quán mà không thay đổi database nguồn. Dữ liệu PostgreSQL không đồng bộ ngược vào SQLite. Database PostgreSQL mới/rỗng sẽ được tạo schema và dữ liệu mẫu khi backend khởi động; hãy nhập dữ liệu của bạn trước khi chạy web nếu muốn giữ dữ liệu hiện tại.

## Khởi động

```powershell
docker compose up -d --build
docker compose ps
docker compose logs --tail 50 web
```

Mở http://127.0.0.1:8080. Cổng này độc lập với Flask local ở cổng 5000. Có thể đổi `MOSA_PORT` trong `.env`.

Image build React ở stage Node.js rồi phục vụ giao diện và API cùng origin bằng Gunicorn. Model và dữ liệu không được đóng gói vào image. Một Gunicorn worker với bốn threads giữ cache model trong cùng process; timeout 120 giây không phải cam kết thời gian phản hồi của model.

Volume `postgres_data` giữ database; `instance/docker` giữ ảnh truy vấn và SQLite cũ; `instance/text-search-model` giữ cache E5 dùng chung với môi trường local. Các thư mục này vẫn còn sau khi dừng hoặc tạo lại container. Cache model có sẵn được tái sử dụng; nếu chưa có model, chuẩn bị một lần:

```powershell
docker compose exec web python scripts/prepare_text_search.py
```

Lệnh chuẩn bị model có thể tải file từ Hugging Face. Khởi động ứng dụng không tự tải model; thiếu model thì tìm từ khoá vẫn hoạt động, còn tìm ngữ nghĩa trả thông báo lỗi. Sau khi thay đổi backend/frontend, chạy lại `docker compose up -d --build`.

## PostgreSQL local

Compose có thêm PostgreSQL 17, database/user mặc định `mosa`. Thêm `POSTGRES_PASSWORD` ngẫu nhiên vào `.env` (xem `.env.example`), rồi chạy:

```powershell
docker compose up -d postgres
docker compose exec postgres psql -U mosa -d mosa
```

Kết nối từ DBeaver hoặc pgAdmin trên Windows: host `127.0.0.1`, port `5433`, database `mosa`, user `mosa`, password lấy từ `.env`. Từ container khác cùng Compose, dùng host `postgres` và port `5432`.

Volume `postgres_data` giữ dữ liệu khi restart/tạo lại container. Không chạy `docker compose down -v` nếu muốn giữ dữ liệu. Các biến `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` chỉ khởi tạo database khi volume còn mới; đổi `.env` không tự đổi mật khẩu/role đã tồn tại.

**Backend hỗ trợ cả SQLite và PostgreSQL.** `DATABASE_URL=postgresql://...` chọn PostgreSQL; không có biến này thì `DATABASE` hoặc file SQLite mặc định được sử dụng. Compose đã cấu hình URL nội bộ cùng `PGDATABASE`, `PGUSER`, `PGPASSWORD`; không dùng `localhost` từ container web để kết nối container postgres. PostgreSQL trên máy này không tự trở thành database cloud mà Render truy cập được.

Lớp dữ liệu dùng Psycopg, giữ tham số truy vấn tách biệt với giá trị. Transaction ghi được tuần tự hoá bằng advisory lock để giữ hành vi chống đặt trùng/vượt tồn kho của SQLite. Các bảng cần sắp thứ tự có thêm cột kỹ thuật `rowid` identity; UUID chính giữ nguyên. Khi khởi động, schema được cập nhật mà không xoá dữ liệu đã nhập. Cách khoá này phù hợp demo; cần đánh giá khoá theo từng bản ghi nếu tăng lưu lượng ghi.

Nếu cần nhập từ bản sao SQLite vào PostgreSQL rỗng, trước hết dừng web, khởi tạo bằng `schema_postgres.sql`, rồi dùng `scripts/export_postgres.py` tạo SQL. Script từ chối ghi đè file xuất và SQL từ chối nhập vào bảng đã có dữ liệu. Không commit/chia sẻ file SQL vì nó chứa dữ liệu tài khoản.

## Dừng các container

```powershell
docker compose down
```

Không xoá các thư mục dữ liệu khi chỉ muốn dừng ứng dụng. Compose này dành cho demo local: cổng chỉ bind localhost, demo payment và recovery demo được bật. Khi đưa lên mạng cần cấu hình HTTPS, secrets và tích hợp phù hợp.

## Bước tiếp theo với Vercel

Vercel không triển khai trực tiếp file Compose và không cung cấp persistent local disk cho SQLite/cache. Docker local không tự làm cho ứng dụng hiện tại phù hợp với Vercel.

Nếu chọn Vercel cho frontend, backend Docker có thể chạy riêng; cần cấu hình proxy `/api` và `/assets`, session/cookie và lưu trữ. Để backend cloud dùng PostgreSQL, đặt `DATABASE_URL` do nhà cung cấp database cấp (kèm SSL theo yêu cầu); không dùng URL nội bộ `postgres:5432` của Compose. Media cần lưu bền hoặc object storage; cần đánh giá cách chạy/cache model E5 trên nền tảng đích. Không đưa file SQL chứa dữ liệu tài khoản vào Git.

Nguồn: https://vercel.com/i/can-you-run-docker-compose-on-vercel
