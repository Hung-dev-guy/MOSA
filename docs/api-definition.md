# Mosa REST API

## Cập nhật 10/11/2026

Tất cả ID là chuỗi UUID 36 ký tự (URL và JSON); không ép Number phía frontend. Payment method COD/ONLINE, status PENDING/PROCESSING/PAID/FAILED/REFUNDED. Endpoint demo vẫn nhận result success/failed/pending; cod/demo được chấp nhận làm alias đầu vào cũ. Cart trả id/status EMPTY hoặc HAS_ITEMS và cart_item_id mỗi dòng. Xem [design-alignment.md](design-alignment.md).

`product_type` nhận pen/notebook/bag/toy/book/electric_device. Không còn Category CRUD hoặc category_id. Tham số category cũ trả 400, không âm thầm bỏ qua bộ lọc; book.details.category là thể loại sách.

## 1. Contract chung
Base /api, same-origin session HttpOnly SameSite=Lax. GET /session trả user, csrf_token, demo. Mọi write dùng X-CSRF-Token; không bật CORS. JSON object, errors {error, code}; 400 input, 401 chưa login, 403 role/CSRF, 404 record không accessible, 409 conflict, 413 upload, 429 throttled. Số tiền integer VND; time ISO UTC. Query không âm, enum allowlist, length bounds. Client không gửi trusted role, stock, payment success hay giá cuối.

## 2. Public/account
| Method path | Input | Output / quyền |
|---|---|---|
| GET /session | – | session bootstrap |
| POST /auth/register | name,email,password | customer; merge guest cart |
| POST /auth/login | email,password | user; rotate csrf |
| POST /auth/logout | – | clear auth |
| PATCH /account | name,email,phone | own profile |
| POST /account/password | current_password,password | đổi password, revoke reset tokens |
| POST /auth/recovery | email | neutral message, demo reset link nếu local |
| POST /auth/reset | token,password | one-time reset, revoke sessions |
| GET /product-types | – | sáu mã loại Product, nhãn và định nghĩa trường nhập |
| GET /products | q,search_mode (keyword/semantic),modality (TEXT/VOICE),product_type,brand,min_price,max_price,available,attribute,color,size,minimum_age,publisher,sort,page | items,total,page,pages |
| GET /products/:id | – | published detail + reviews |
| POST /search/image | multipart image | ranked published products, method label |
| GET /cart | – | lines,subtotal |
| POST /cart/items | product_id,quantity | repeated addition merges |
| PATCH /cart/items/:id | quantity | replace quantity |
| DELETE /cart/items/:id | – | remove |

## 3. Transactional
| Method path | Input | Output |
|---|---|---|
| POST /checkout/quote | {} | subtotal,shipping,total |
| POST /orders | recipient,phone,address,payment_method,expected_subtotal + Idempotency-Key header | order + payment pending/COD |
| GET /orders | – | own orders |
| GET /orders/:id | – | own details/history/shipment |
| POST /orders/:id/cancel | – | cancel if eligible |
| POST /orders/:id/payment/retry | – | reserve again if required, same order pending |
| POST /demo/payments/:id | result: success/failed/pending,event_id | authenticated owner; demo only |
| POST /products/:id/reviews | rating,comment | delivered purchase only |
| GET /notifications | – | own in-app events |
| POST /support | order_id nullable,subject,message | own service case |
| GET /support | – | own cases |

Payment adapter demo không nhận callback Internet. Production callback phải có signature verification, provider correlation/amount check và event dedupe; chưa có provider nên không mở endpoint giả xác minh.

## 4. Staff
Prefix /staff. GET /overview trả datasets theo role, không trả password/token và không trả customer PII cho warehouse/manager. Admin có tất cả; sales orders/support/exceptions/shipping; warehouse inventory/supply/fulfilment; manager reports.
| Method path | Input / policy |
|---|---|
| POST /staff/products; PATCH /staff/products/:id | name,product_type,details,description,brand,price,selling_unit,origin,material,attributes,image,status hoặc published. Không edit stock trực tiếp |
| PATCH /staff/customers/:id | active boolean; only customer role |
| POST /staff/inventory | product_id,quantity (signed adjustment),kind receipt/adjustment,reason; không giảm dưới reserved |
| POST /staff/orders/:id/status | status picking/packed/shipped/delivered; transitions guarded |
| POST /staff/orders/:id/shipment | provider,tracking_code; eligible dispatched order |
| POST /staff/orders/:id/tracking | event_id,status in_transit/delivered/exception,message |
| POST /staff/supply | supplier,product_id,quantity |
| POST /staff/supply/:id/receive | –; one receipt only |
| PATCH /staff/support/:id | status open/in_progress/closed,reply |
| POST /staff/exceptions | order_id nullable,product_id nullable,reason,follow_up; service case with audit |
| GET /staff/reports | from YYYY-MM-DD,to YYYY-MM-DD | UTC inclusive dates, totals, counts, inventory/service data |
| GET /staff/reports.csv | same period | CSV no customer fields |

## 5. Example
```json
{"recipient":"Nguyễn An","phone":"0901234567","address":"12 Nguyễn Trãi, Hà Nội","payment_method":"ONLINE","expected_subtotal":55000}
```
Mã giảm giá đã được bỏ theo phạm vi thiết kế; request có promo khác rỗng trả 400. Quote không giữ tồn kho. Khi checkout response mất, gửi lại cùng Idempotency-Key và payload, backend trả cùng order; cùng key khác payload bị 409. Cần GET detail để đối soát khi mạng không ổn định.

## Semantic text search (11/11/2026)

`GET /api/products?q=...&search_mode=semantic` sử dụng embedding văn bản local. `search_mode=keyword` là mặc định và giữ đối sánh từ khóa hiện có. TEXT/VOICE là phương thức nhập, độc lập với search_mode. Response thêm `search_mode`, semantic thêm `encoder_version` và `items[].similarity` (cosine, không phải xác suất chính xác).

Semantic mặc định sắp xếp `relevance`; hỗ trợ `newest`, `price_asc`, `price_desc`, `name` trên tập đạt ngưỡng tương đồng. `sort=relevance` chỉ hợp lệ cho semantic có truy vấn. Bộ lọc explicit luôn áp dụng trước xếp hạng/phân trang; không tự diễn giải số tiền trong câu thành điều kiện lọc. Truy vấn rỗng duyệt catalogue theo keyword. Model lỗi/chưa tải trả 503, không âm thầm đổi chế độ. UI cung cấp chuyển sang từ khóa. Không thay đổi API tìm ảnh.

Xem [thiết lập và giới hạn](semantic-text-search.md).
