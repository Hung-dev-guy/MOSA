from scripts.update_product_descriptions import description

def test_description_uses_purpose_without_repeating_fields():
    assert description({'name':'Bút gel đỏ 0.5mm', 'product_type':'pen'}).startswith('Dùng để viết và ghi chép')
    assert description({'name':'Máy tính 12 số', 'product_type':'electric_device'}).startswith('Dùng để thực hiện các phép tính')
    assert description({'name':'Giấy in A4', 'product_type':None}).startswith('Dùng để in tài liệu')
    assert description({'name':'Sổ tay', 'product_type':'notebook'}) != description({'name':'Bút gel', 'product_type':'pen'})


def test_descriptions_are_at_least_40_words_and_do_not_repeat_properties():
    cases = [('Bút chì', 'pen'), ('Sổ tay', 'notebook'), ('Ba lô', 'bag'), ('Đồ chơi', 'toy'), ('Sách', 'book'), ('Máy tính', 'electric_device'), ('Giấy in', None), ('Kẹp giấy', None)]
    for name, kind in cases:
        text = description({'name': name, 'product_type': kind})
        assert len(text.split()) >= 40, (name, text)
        assert all(label not in text for label in ('Chất liệu:', 'Kích thước:', 'Màu sắc:', 'Thương hiệu:'))
