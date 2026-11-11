"""Build product descriptions from stored catalogue facts, preserving existing database state."""
import json
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.data_infrastructure.database.connection import connect
from backend.shared.product_types import PRODUCT_FIELDS
from scripts.backup import backup

def description(row, details=None):
    """Describe purpose only; never repeat structured properties or invent claims."""
    name = row['name'].casefold()
    kind = row['product_type']
    patterns = [
        (('bút chì màu', 'bút màu'), 'Dùng để tô màu, vẽ và thể hiện ý tưởng trên giấy.'),
        (('bút chì',), 'Dùng để viết, phác thảo và ghi chép trong học tập hoặc công việc.'),
        (('bút dạ quang', 'bút highlight'), 'Dùng để đánh dấu nội dung cần chú ý khi đọc và ghi chép.'),
        (('giấy in',), 'Dùng để in tài liệu phục vụ học tập và công việc.'),
        (('thước',), 'Dùng để đo và hỗ trợ kẻ đường thẳng trong học tập hoặc công việc.'),
        (('bìa còng', 'bìa hồ sơ'), 'Dùng để sắp xếp và lưu giữ tài liệu.'),
        (('kéo',), 'Dùng để cắt giấy và thực hiện các hoạt động thủ công.'),
        (('băng keo',), 'Dùng để dán và trang trí trong các hoạt động thủ công.'),
        (('kẹp giấy',), 'Dùng để kẹp và sắp xếp các tờ tài liệu.'),
        (('màu nước',), 'Dùng để vẽ, tô màu và thực hiện các hoạt động sáng tạo.'),
        (('máy tính',), 'Dùng để thực hiện các phép tính phục vụ học tập hoặc công việc.'),
        (('máy hủy giấy', 'máy huỷ giấy'), 'Dùng để hủy tài liệu giấy.'),
        (('tô màu',), 'Dùng để tô màu và thực hành các hoạt động sáng tạo.'),
    ]
    context = {
        'pen': 'Phù hợp khi cần ghi lại nội dung, trình bày bài học hoặc thực hiện công việc trên giấy. Có thể dùng tại bàn học, lớp học hay nơi làm việc, tùy theo mục đích viết và dụng cụ đi kèm.',
        'notebook': 'Có thể dùng để ghi bài, lập kế hoạch, lưu nội dung cần nhớ hoặc sắp xếp ý tưởng theo từng chủ đề. Phù hợp cho việc ghi chép cá nhân trong quá trình học tập và làm việc hằng ngày.',
        'bag': 'Có thể sử dụng để mang sách, tài liệu hoặc vật dụng cá nhân khi đi học, đi làm hay di chuyển. Việc sắp xếp đồ dùng bên trong giúp người dùng chuẩn bị và tìm lại vật dụng cần thiết.',
        'toy': 'Có thể lựa chọn cho thời gian vui chơi cá nhân hoặc cùng gia đình, tùy theo cách chơi của sản phẩm. Người lớn nên xem hướng dẫn và lựa chọn hoạt động phù hợp trước khi cho trẻ sử dụng.',
        'book': 'Người đọc có thể sử dụng trong thời gian học tập hoặc giải trí, đọc theo từng phần và lưu lại những nội dung quan tâm. Sản phẩm phù hợp để bổ sung vào tủ sách cá nhân hoặc làm quà tặng.',
        'electric_device': 'Người dùng có thể tham khảo hướng dẫn của nhà sản xuất để thực hiện thao tác phù hợp với chức năng được cung cấp. Sản phẩm hỗ trợ công việc hằng ngày khi cần sử dụng đúng mục đích của thiết bị.',
        None: 'Có thể sử dụng trong các hoạt động hằng ngày liên quan đến công dụng của sản phẩm. Người dùng nên lựa chọn cách dùng phù hợp với nhu cầu thực tế và hướng dẫn đi kèm, nếu có.',
    }
    for keywords, result in patterns:
        if any(word in name for word in keywords):
            return result + ' ' + context.get(kind, context[None])
    purpose = {
        'pen': 'Dùng để viết và ghi chép trong học tập hoặc công việc.',
        'notebook': 'Dùng để ghi chép, lưu lại ý tưởng và sắp xếp nội dung học tập hoặc công việc.',
        'bag': 'Dùng để mang theo và sắp xếp đồ dùng khi đi học, đi làm hoặc di chuyển.',
        'toy': 'Dùng trong hoạt động vui chơi và giải trí.',
        'book': 'Dùng để đọc, tìm hiểu nội dung và khám phá kiến thức hoặc câu chuyện.',
        'electric_device': 'Dùng hỗ trợ các hoạt động học tập hoặc công việc theo chức năng của thiết bị.',
        None: 'Dùng hỗ trợ các hoạt động học tập, công việc hoặc sáng tạo.',
    }.get(kind, 'Dùng hỗ trợ các hoạt động học tập, công việc hoặc sáng tạo.')
    return purpose + ' ' + context.get(kind, context[None])


def main():
    dbpath = ROOT / 'instance/mosa.sqlite'
    dest = Path(str(dbpath) + '.pre-descriptions-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.sqlite')
    backup(dbpath, dest)
    db = connect(dbpath)
    counts = Counter()
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            products = db.execute('SELECT * FROM products').fetchall()
            for row in products:
                kind = row['product_type']
                detail = db.execute('SELECT * FROM ' + kind + ' WHERE product_id=?', (row['id'],)).fetchone() if kind in PRODUCT_FIELDS else None
                details = {k: detail[k] for k in detail.keys() if k != 'product_id'} if detail else {}
                db.execute('UPDATE products SET description=?,updated_at=? WHERE id=?', (description(row, details), datetime.now(timezone.utc).isoformat(timespec='seconds'), row['id']))
                counts[kind or 'unclassified'] += 1
            if db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Foreign-key validation failed')
        print(json.dumps({'updated':sum(counts.values()),'counts':dict(counts),'backup':str(dest)},ensure_ascii=True))
    finally:
        db.close()


if __name__ == '__main__':
    main()
