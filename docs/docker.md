# Chạy Mosa bằng Docker

Chạy các lệnh từ thư mục `PTTKHTTT-APP`. Docker Desktop cần ở chế độ Linux containers.

## Chuẩn bị lần đầu

Tạo `.env` với secret ngẫu nhiên (lệnh không ghi đè nếu file đã có):

```powershell
python -c "from pathlib import Path; import secrets; p=Path('.env'); p.exists() or p.write_text('MOSA_SECRET_KEY='+secrets.token_hex(32)+'\nMOSA_PORT=8080\n', encoding='utf-8')"
```

Nếu đã có `.env`, thêm `MOSA_SECRET_KEY` với giá trị ngẫu nhiên. Không commit file này.

Container sử dụng database riêng trong `instance/docker/mosa.sqlite`. Để bắt đầu bằng bản sao dữ liệu local hiện tại:

```powershell
.\.venv\Scripts\python.exe scripts/backup.py instance/mosa.sqlite instance/docker/mosa.sqlite
```

Chỉ chạy lệnh sao lưu khi file đích chưa tồn tại. SQLite backup API tạo bản sao nhất quán mà không thay đổi database nguồn. Nếu không sao chép, ứng dụng tạo database demo mới khi khởi động. Thay đổi trong Docker không được đồng bộ ngược vào database local.

## Khởi động

```powershell
docker compose up -d --build
docker compose ps
docker compose logs --tail 50 web
```

Mở http://127.0.0.1:8080. Cổng này độc lập với Flask local ở cổng 5000. Có thể đổi `MOSA_PORT` trong `.env`.

Image build React ở stage Node.js rồi phục vụ giao diện và API cùng origin bằng Gunicorn. Model và dữ liệu không được đóng gói vào image. Một Gunicorn worker với bốn threads giữ cache model trong cùng process; timeout 120 giây không phải cam kết thời gian phản hồi của model.

`instance/docker` giữ database và ảnh truy vấn; `instance/text-search-model` giữ cache E5 dùng chung với môi trường local. Các thư mục này vẫn còn sau khi dừng hoặc tạo lại container. Cache model có sẵn được tái sử dụng; nếu chưa có model, chuẩn bị một lần:

```powershell
docker compose exec web python scripts/prepare_text_search.py
```

Lệnh chuẩn bị model có thể tải file từ Hugging Face. Khởi động ứng dụng không tự tải model; thiếu model thì tìm từ khoá vẫn hoạt động, còn tìm ngữ nghĩa trả thông báo lỗi. Sau khi thay đổi backend/frontend, chạy lại `docker compose up -d --build`.

## Dừng

```powershell
docker compose down
```

Không xoá các thư mục dữ liệu khi chỉ muốn dừng ứng dụng. Compose này dành cho demo local: cổng chỉ bind localhost, demo payment và recovery demo được bật. Khi đưa lên mạng cần cấu hình HTTPS, secrets và tích hợp phù hợp.

## Bước tiếp theo với Vercel

Vercel không triển khai trực tiếp file Compose và không cung cấp persistent local disk cho SQLite/cache. Docker local không tự làm cho ứng dụng hiện tại phù hợp với Vercel.

Phương án giữ nguyên code nhiều nhất là chạy toàn bộ container trên máy chủ có ổ đĩa lưu bền. Nếu vẫn chọn Vercel cho frontend, backend Docker có thể chạy riêng; cần cấu hình proxy `/api` và `/assets`, session/cookie và lưu trữ. Nếu chuyển cả backend lên Vercel, cần thay SQLite bằng database dịch vụ, dùng object storage cho media và đánh giá lại cách chạy model E5.

Nguồn: https://vercel.com/i/can-you-run-docker-compose-on-vercel
