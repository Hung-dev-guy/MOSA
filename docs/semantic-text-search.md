# Semantic text search — 11/11/2026

Luồng tham chiếu từ `afd-text-search.vpp`: Submit text query and explicit filters → Query valid? → Search by keywords or meaning → search successful? → Matches found? → Display matching products; lỗi cho phép retry/browsing, không có kết quả được báo rõ.

## Cách chạy

Chạy `run.ps1`, hoặc cài `requirements.txt` rồi chạy `.venv/Scripts/python.exe scripts/prepare_text_search.py`. Script tái sử dụng cache nếu đã đủ; lần đầu tải model từ Hugging Face. Không cần API key. Model/các file tokenizer nằm trong `instance/text-search-model/`, không đưa vào Git. Sau khi tải xong, runtime dùng `local_files_only=True`; văn bản truy vấn và sản phẩm không được gửi đến dịch vụ embedding ngoài.

Mô hình là `intfloat/multilingual-e5-small`, bản ONNX FP32 chính thức của intfloat, đăng ký custom model trong FastEmbed, 384 chiều. Đây là embedding model thật, không phải bảng từ đồng nghĩa. Nguồn: [model card](https://huggingface.co/intfloat/multilingual-e5-small), [FastEmbed supported models](https://qdrant.github.io/fastembed/examples/Supported_Models/).

## Hành vi

- Thanh tìm kiếm có selector Từ khóa / Ngữ nghĩa; URL `search_mode=keyword|semantic`. Mặc định keyword để giữ hành vi cũ; mode lưu trên URL nên back/reload giữ lựa chọn đã tìm.
- TEXT và VOICE dùng cùng luồng text search. IMAGE giữ baseline cũ, không dùng text embeddings.
- Semantic nhận câu diễn đạt nhu cầu; chỉ mục lấy tên, thương hiệu, đơn vị bán, thuộc tính và mô tả đã xuất bản. Mô hình giới hạn 512 token nên thông tin tên/thuộc tính đứng trước mô tả.
- Tận dụng bộ lọc/kiểm tra đầu vào hiện có trước khi lấy embedding và xếp hạng cosine; không ép câu tự nhiên phải trùng từng từ trong tên. Không tự nới bộ lọc hoặc trích xuất điều kiện giá từ câu.
- Ngưỡng demo cosine 0.85 loại ứng viên thấp; mặc định xếp theo độ phù hợp, tie-break theo product_id. Có thể sắp xếp giá/tên/mới nhất trên tập đạt ngưỡng. Phân trang 8 sản phẩm.
- Cache embedding tối đa 8 tập nội dung trong bộ nhớ. Nội dung thay đổi tạo key mới; mọi yêu cầu đọc lại sản phẩm ACTIVE và giá/tồn kho hiện hành. Cache chỉ chứa vector, không dùng dữ liệu giá/tồn kho cũ để trả kết quả. Một lock bảo vệ khởi tạo và inference đồng thời trong mỗi process.
- SearchQuery ghi encoder_version; SearchResult ghi cosine và lời giải thích semantic. Không cần sửa schema hoặc thêm SEMANTIC vào SearchModality.
- Không có kết quả hiển thị empty state. Model thiếu/lỗi trả 503 với retry và chuyển sang từ khóa; không âm thầm dùng keyword rồi gọi là semantic.

## Kiểm chứng và giới hạn

`tests/test_semantic_search.py` dùng vector kiểm soát để kiểm tra nhánh keyword/semantic, thứ hạng cosine, bộ lọc, phân trang, validation trước inference, giá mới/archived, query logs và lỗi model. Playwright kiểm tra hai chế độ, filter, reload và fallback trên desktop/mobile; luồng semantic thành công dùng model local thật. Các probe thủ công dùng câu tiếng Việt và truy vấn ngoài catalogue để kiểm tra thực tế.

Các kiểm tra này không chứng minh chất lượng relevance tổng quát. Ngưỡng 0.85 chưa được hiệu chỉnh bằng tập nhãn; mô hình có thể trả sản phẩm gần nghĩa nhưng chưa đúng nhu cầu hoặc bỏ sót sản phẩm. Chưa có đo Precision@k/Recall@k hay benchmark tải production. Cần tập truy vấn tiếng Việt có nhãn, bao gồm mã/thông số chính xác, câu mơ hồ và ngoài phạm vi để đánh giá trước khi đổi model/ngưỡng. Lần đầu inference hoặc đổi tập ứng viên cần tính embedding nên chậm hơn các truy vấn tiếp theo; với catalogue lớn hơn cần chỉ mục vector lưu bền và cập nhật theo thay đổi sản phẩm.


## Kiểm tra lịch sử trước khi đổi E5 (MiniLM, 11/11/2026)

Đã kiểm tra bằng bản sao nhất quán của DB runtime có 124 sản phẩm ACTIVE, bật `HF_HUB_OFFLINE=1` và chặn `socket.connect` trong toàn bộ quá trình inference. Model tạo vector 384 chiều, các phần tử hữu hạn; API semantic trả encoder_version đúng. Truy vấn “dụng cụ để ghi chép bài học” trả 4 kết quả semantic (đầu tiên Sổ tay lò xo Pastel A5 120 trang), trong khi keyword không có kết quả. Điều này xác nhận thực thi model, không phải đánh giá chất lượng tổng quát.

Lần tính embedding corpus đầu đo được 15.251 giây; các truy vấn kế tiếp cùng corpus khoảng 0.06 giây. Frontend dành timeout 60 giây riêng cho semantic để tránh ngắt khởi tạo ở giới hạn 15 giây của keyword. Playwright có ca giữ phản hồi semantic hơn 15 giây để kiểm tra hành vi này.

## Chuyển sang E5-small — 11/11/2026

- Mean pooling và L2 normalization, ONNX FP32 384 chiều. Truy vấn thêm `query: `, sản phẩm thêm `passage: `, kể cả tiếng Việt. Runtime vẫn offline, không gửi truy vấn ra ngoài.
- MODEL_VERSION mới phân biệt model, pooling và tiền tố. Vector chỉ cache trong RAM; khởi động lại app tạo vector mới, không trộn vector MiniLM. Không cần sửa schema database.
- Kiểm tra model thật với socket.connect bị chặn: tính vector cho 333 sản phẩm ACTIVE mất 20.67 giây trên máy hiện tại. Tổng database có 341 sản phẩm, gồm cả sản phẩm không ACTIVE.
- Bốn câu về bút, balo, máy tính, sổ có kết quả đầu đúng nhóm, cosine khoảng 0.878–0.907. Hai câu ngoài phạm vi về vé máy bay và thuốc có điểm cao nhất 0.824 và 0.830.
- Ngưỡng thử nghiệm đổi từ 0.35 sang 0.85: ở ngưỡng cũ cả 333 ứng viên đều vượt ngưỡng trong sáu câu thử. Đây chưa phải benchmark hoặc ngưỡng tối ưu; cần tập truy vấn có nhãn lớn hơn để đánh giá recall/precision.
- Khởi động lại backend đang chạy để nạp model và bỏ cache cũ. Không cần build lại frontend.
