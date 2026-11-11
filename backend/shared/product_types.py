"""The six Product specializations shared by catalogue validation and its public UI contract."""
PRODUCT_FIELDS = {
    'pen': {'color': False, 'type': True},
    'notebook': {'page_num': True, 'size': True, 'type': True},
    'bag': {'size': True, 'pattern': False},
    'toy': {'type': True, 'minimum_age': False},
    'book': {'category': True, 'minimum_age': False, 'publisher': True},
    'electric_device': {'minimum_age': False, 'weight': False},
}
PRODUCT_LABELS = {'pen':'Bút','notebook':'Sổ / vở','bag':'Túi','toy':'Đồ chơi','book':'Sách','electric_device':'Thiết bị điện'}
FIELD_LABELS = {'color':'Màu sắc','type':'Loại','page_num':'Số trang','size':'Kích thước','pattern':'Hoạ tiết','minimum_age':'Độ tuổi tối thiểu','category':'Thể loại sách','publisher':'Nhà xuất bản','weight':'Khối lượng (g)'}
NUMBER_FIELDS = {'page_num','minimum_age','weight'}


def product_types():
    return [{'id':kind,'name':PRODUCT_LABELS[kind],'fields':[
        {'id':field,'label':FIELD_LABELS[field],'required':required,
         'type':'number' if field in NUMBER_FIELDS else 'text',
         'minimum':1 if field=='page_num' else 0,
         'maximum':1000000 if field in NUMBER_FIELDS else None,
         'max_length':150 if field=='publisher' else 100 if field in ['category','pattern'] else 50}
        for field,required in fields.items()]} for kind,fields in PRODUCT_FIELDS.items()]
