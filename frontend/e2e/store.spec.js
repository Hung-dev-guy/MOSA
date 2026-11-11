import {test,expect} from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';

async function ready(page,url='/'){
  await page.goto(url);
  await expect(page.getByRole('searchbox')).toHaveCount(0);
  await expect(page.getByRole('textbox',{name:'Tìm kiếm sản phẩm',exact:true})).toBeVisible();
}
async function login(page,role='customer'){
  await ready(page,'/login');
  await page.getByLabel('Email',{exact:true}).fill(role+'@mosa.local');
  await page.getByLabel('Mật khẩu',{exact:true}).fill('Mosa@12345');
  await page.getByRole('button',{name:'Đăng nhập',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Tài khoản của bạn'})).toBeVisible();
}
async function overflow(page){expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();}

async function screenshot(page,file){
  await page.evaluate(async()=>{for(let y=0;y<document.body.scrollHeight;y+=500){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,30));}window.scrollTo(0,0);await Promise.all(Array.from(document.images).map(i=>i.decode().catch(()=>{})));});
  await page.screenshot({path:file,fullPage:true});
}

test('catalogue, filters, empty result, detail and responsive layout',async({page},info)=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await ready(page);
  await expect(page.locator('.product-card')).toHaveCount(8);
  await overflow(page);
  const evidence=path.resolve('../docs/evidence');fs.mkdirSync(evidence,{recursive:true});
  await screenshot(page,path.join(evidence,info.project.name+'-home.png'));
  await page.getByRole('textbox',{name:'Tìm kiếm sản phẩm',exact:true}).fill('but');
  await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Kết quả cho “but”'})).toBeVisible();
  await page.getByLabel('Thương hiệu',{exact:true}).selectOption('Thiên Long');
  await expect(page.locator('.product-card')).toHaveCount(3);
  await page.getByLabel('Giá cao nhất',{exact:true}).fill('15000');
  await expect(page.locator('.product-card')).toHaveCount(1);
  await page.locator('.product-name').click();
  await expect(page.getByRole('heading',{name:'Bút gel Thiên Long FlexOffice 0.5mm'})).toBeVisible();
  await expect(page.locator('.specs')).toContainText('0.5mm');
  await overflow(page);
  await page.getByRole('textbox',{name:'Tìm kiếm sản phẩm',exact:true}).fill('zzzzzz');
  await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click();
  await expect(page.getByText('Chưa tìm thấy sản phẩm phù hợp.',{exact:false})).toBeVisible();
  expect(errors).toEqual([]);
});

test('guest cart, register, checkout, payment and personal order',async({page},info)=>{
  await ready(page,'/product/78cde59a-3138-587c-b5a2-be9ad8ee4389');
  await page.getByRole('button',{name:'Thêm vào giỏ hàng',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Đã thêm');
  await ready(page,'/cart');
  await expect(page.getByText('Sách khám phá khoa học',{exact:true})).toBeVisible();
  await page.getByRole('link',{name:'Tiến hành đặt hàng',exact:false}).click();
  await expect(page.getByRole('heading',{name:'Đăng nhập để tiếp tục'})).toBeVisible();
  await ready(page,'/register');
  await page.getByLabel('Họ và tên',{exact:true}).fill('Khách E2E');
  await page.getByLabel('Email',{exact:true}).fill('e2e-'+info.project.name+'-'+Date.now()+'@example.com');
  await page.getByLabel('Mật khẩu',{exact:true}).fill('E2EPassword123');
  await page.getByRole('button',{name:'Đăng ký',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Tài khoản của bạn'})).toBeVisible();
  await ready(page,'/checkout');
  await page.getByLabel('Số điện thoại',{exact:true}).fill('0901234567');
  await page.getByLabel('Địa chỉ giao hàng',{exact:true}).fill('12 Nguyễn Trãi, Thanh Xuân, Hà Nội');
  await expect(page.getByLabel('Mã giảm giá',{exact:true})).toHaveCount(0);
  await expect(page.getByRole('link',{name:'Ưu đãi Mosa',exact:true})).toHaveCount(0);
  await expect(page.locator('.summary-total')).toContainText('114.000');
  await page.getByLabel('Thanh toán trực tuyến mô phỏng',{exact:false}).check();
  await overflow(page);
  await page.getByRole('button',{name:'Xác nhận đặt hàng',exact:true}).click();
  await expect(page.getByText('MÔ PHỎNG THANH TOÁN',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Ghi nhận kết quả mô phỏng',exact:true}).click();
  await expect(page.getByRole('heading',{name:/Đơn hàng MOSA-/})).toBeVisible();
  await expect(page.locator('.status.PAID')).toContainText('Đã thanh toán');
  await expect(page.getByText('Chưa có vận đơn.',{exact:false})).toBeVisible();
  await overflow(page);
  await page.screenshot({path:path.resolve('../docs/evidence/'+info.project.name+'-order.png'),fullPage:true});
});

test('voice fallback, mocked transcript and image similarity',async({page})=>{
  await page.addInitScript(()=>{window.SpeechRecognition=undefined;window.webkitSpeechRecognition=undefined;});
  await ready(page);
  await page.getByRole('button',{name:'Tìm bằng giọng nói'}).click();
  await expect(page.getByText('Trình duyệt chưa hỗ trợ giọng nói.',{exact:false})).toBeVisible();
  await page.evaluate(()=>{window.SpeechRecognition=class {start(){this.onresult({results:[[{transcript:'bút xanh'}]]});this.onend();}abort(){}};});
  await page.getByRole('button',{name:'Tìm bằng giọng nói'}).click();
  await expect(page.getByRole('textbox',{name:'Tìm kiếm sản phẩm',exact:true})).toHaveValue('bút xanh');
  await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Kết quả cho “bút xanh”'})).toBeVisible();
  const chooser=page.waitForEvent('filechooser');
  await page.locator('.search').getByRole('button',{name:'Tìm bằng hình ảnh',exact:true}).click();
  await (await chooser).setFiles(path.resolve('public/assets/pen-blue.png'));
  await expect(page.locator('.catalogue-tools input[type=file]')).toHaveCount(0);
  const preview=page.getByRole('img',{name:'Ảnh đã chọn để tìm sản phẩm',exact:true});
  await expect(preview).toBeVisible();
  await expect.poll(()=>preview.evaluate(img=>img.naturalWidth)).toBeGreaterThan(0);
  await expect(page.locator('.search-image-preview')).toContainText('pen-blue.png');
  await overflow(page);
  await expect(page.getByText('So khớp màu và bố cục;',{exact:false})).toBeVisible();
  await expect(page.locator('.product-name').filter({hasText:'Bút gel Thiên Long'})).toBeVisible();
  await page.getByLabel('Thương hiệu',{exact:true}).selectOption('Thiên Long');
  await expect(page.getByText('So khớp màu và bố cục;',{exact:false})).toBeVisible();
  await expect(preview).toBeVisible();
  const replacement=page.waitForEvent('filechooser');
  await page.getByRole('button',{name:'Đổi ảnh',exact:true}).click();
  await (await replacement).setFiles(path.resolve('public/assets/notebook.png'));
  await expect(page.locator('.search-image-preview')).toContainText('notebook.png');
  await expect.poll(()=>preview.evaluate(img=>img.naturalWidth)).toBeGreaterThan(0);
  await page.getByRole('textbox',{name:'Tìm kiếm sản phẩm',exact:true}).fill('sổ');
  await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Kết quả cho “sổ”'})).toBeVisible();
  await expect(page.getByText('So khớp màu và bố cục;',{exact:false})).toHaveCount(0);
  await expect(preview).toHaveCount(0);
});

test('admin catalogue, stock and report workspace',async({page},info)=>{
  await login(page,'admin');
  await page.getByRole('link',{name:/Mở khu vực quản trị/}).click();
  await expect(page.getByRole('heading',{name:'Quản lý cửa hàng'})).toBeVisible();
  const first=page.getByRole('row').filter({hasText:'Bút gel Thiên Long FlexOffice'});
  await first.getByRole('button',{name:'Chỉnh sửa'}).click();
  await page.getByLabel('Giá VND',{exact:true}).fill('12000');
  await page.getByRole('button',{name:'Cập nhật sản phẩm',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Đã lưu thay đổi');
  await page.getByRole('tab',{name:'Tồn kho',exact:true}).click();
  await page.getByLabel('Sản phẩm',{exact:true}).selectOption('6d6cec0d-03a6-5c54-bd6b-aeeefdfa5086');
  await page.getByLabel('Số lượng',{exact:true}).fill('5');
  await page.getByLabel('Lý do',{exact:true}).fill('Nhập hàng kiểm thử E2E');
  await page.getByRole('button',{name:'Ghi nhận biến động',exact:true}).click();
  await expect(page.getByRole('cell',{name:/Nhập hàng kiểm thử E2E/})).toBeVisible();
  await page.getByRole('tab',{name:'Báo cáo',exact:true}).click();
  await expect(page.getByText('Doanh thu đã thu',{exact:true})).toBeVisible();
  await overflow(page);
  await page.screenshot({path:path.resolve('../docs/evidence/'+info.project.name+'-staff.png'),fullPage:true});
  const download=page.waitForEvent('download');
  await page.getByRole('link',{name:'Tải CSV',exact:true}).click();
  expect((await download).suggestedFilename()).toBe('mosa-report.csv');
});

test('warehouse role controls and support enquiry',async({page})=>{
  await login(page,'warehouse');
  await ready(page,'/staff');
  await expect(page.getByRole('tab',{name:'Đơn hàng',exact:true})).toBeVisible();
  await expect(page.getByRole('tab',{name:'Khách hàng',exact:true})).toHaveCount(0);
  await expect(page.getByRole('tab',{name:'Báo cáo',exact:true})).toHaveCount(0);
  await ready(page,'/support');
  await page.getByLabel('Chủ đề',{exact:true}).fill('Hỗ trợ E2E');
  await page.getByLabel('Nội dung',{exact:true}).fill('Xin tư vấn về sản phẩm văn phòng phẩm.');
  await page.getByRole('button',{name:'Gửi yêu cầu hỗ trợ',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Hỗ trợ E2E',exact:true})).toBeVisible();
});


test('six product types drive navigation and filtering without legacy categories',async({page})=>{
  const oldRequests=[];page.on('request',r=>{if(r.url().includes('/api/categories'))oldRequests.push(r.url());});
  await ready(page);
  const types=await (await page.request.get('/api/product-types')).json();
  expect(types.map(t=>t.id)).toEqual(['pen','notebook','bag','toy','book','electric_device']);
  await page.getByRole('button',{name:'Danh mục sản phẩm',exact:true}).click();
  for(const type of types){
    await expect(page.locator('.category-dropdown').getByRole('link',{name:type.name,exact:true})).toHaveAttribute('href','/?product_type='+type.id);
    await expect(page.locator('footer').getByRole('link',{name:type.name,exact:true})).toHaveAttribute('href','/?product_type='+type.id);
  }
  await page.locator('.category-dropdown').getByRole('link',{name:'Sách',exact:true}).click();
  await expect(page).toHaveURL(/product_type=book/);
  for(const type of types){
    const response=page.waitForResponse(r=>r.url().includes('/api/products?')&&new URL(r.url()).searchParams.get('product_type')===type.id);
    await page.locator('.category-chips').getByRole('button',{name:type.name,exact:true}).click();
    const result=await (await response).json();
    expect(result.total).toBeGreaterThan(0);
    expect(result.items.every(p=>p.product_type===type.id)).toBeTruthy();
    await expect(page.locator('.product-card')).toHaveCount(result.items.length);
  }
  expect(oldRequests).toEqual([]);
  await overflow(page);
});

test('admin creates every specialization using the shared type fields',async({page},info)=>{
  test.setTimeout(90000);
  await login(page,'admin');await ready(page,'/staff');
  await expect(page.getByRole('tab',{name:'Danh mục',exact:true})).toHaveCount(0);
  await expect(page.getByLabel('Nhóm duyệt sản phẩm',{exact:true})).toHaveCount(0);
  const details={pen:{color:'tím',type:'Gel'},notebook:{page_num:120,size:'A5',type:'Lò xo'},bag:{size:'20 x 30 cm',pattern:'Trơn'},toy:{type:'Xếp hình',minimum_age:6},book:{category:'Khoa học',minimum_age:6,publisher:'Kim Đồng'},electric_device:{minimum_age:6,weight:300}};
  const images={pen:'pen-blue',notebook:'notebook',bag:'bag',toy:'toy',book:'book',electric_device:'electric-device'};
  const types=await (await page.request.get('/api/product-types')).json();
  for(const type of types){
    const name='E2E '+info.project.name+' '+type.id+' '+Date.now();
    await page.getByLabel('Tên sản phẩm',{exact:true}).fill(name);
    await page.getByLabel('Giá VND',{exact:true}).fill('129000');
    await page.getByLabel('Loại sản phẩm',{exact:true}).selectOption(type.id);
    await expect(page.getByLabel('Tên sản phẩm',{exact:true})).toHaveValue(name);
    await expect(page.getByLabel('Giá VND',{exact:true})).toHaveValue('129000');
    await page.getByLabel('Thương hiệu',{exact:true}).fill('Mosa');
    await page.getByLabel('Đơn vị bán',{exact:true}).fill(type.id==='book'?'Cuốn':'Chiếc');
    for(const field of type.fields)await page.getByLabel(field.label,{exact:true}).fill(String(details[type.id][field.id]));
    await page.getByLabel('Ảnh minh hoạ',{exact:true}).selectOption('/assets/'+images[type.id]+'.png');
    await page.getByLabel('Xuất bản trên cửa hàng',{exact:true}).check();
    const response=page.waitForResponse(r=>r.url().endsWith('/api/staff/products')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Tạo sản phẩm',exact:true}).click();
    const saved=await response;expect(saved.status()).toBe(200);
    const product=await saved.json();expect(product.product_type).toBe(type.id);expect(product.details).toEqual(details[type.id]);expect(product.category_id).toBeUndefined();
    const view=await (await page.request.get('/api/products/'+product.id)).json();expect(view.name).toBe(name);
    await expect(page.getByRole('row').filter({hasText:name})).toBeVisible();
  }
  await overflow(page);
});

test('microphone shows animated waves until recognition ends',async({page})=>{
  await page.addInitScript(()=>{
    window.SpeechRecognition=class {
      start(){window.testSpeech=this;}
      abort(){this.onend();}
    };
  });
  await ready(page);
  const mic=page.getByRole('button',{name:'Tìm bằng giọng nói',exact:true});
  const wave=page.getByRole('status',{name:'Đang nghe giọng nói',exact:true});
  await mic.click();
  await expect(wave).toBeVisible();
  await expect(mic).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('.voice-wave i')).toHaveCount(9);
  await expect(page.locator('.voice-wave i').first()).toHaveCSS('animation-name','voice-wave-pulse');
  await overflow(page);
  await page.evaluate(()=>window.testSpeech.onresult({results:[[{transcript:'bút xanh'}]]}));
  await expect(wave).toHaveCount(0);
  await expect(page.getByRole('textbox',{name:'Tìm kiếm sản phẩm',exact:true})).toHaveValue('bút xanh');
  await mic.click();
  await expect(wave).toBeVisible();
  await mic.click();
  await expect(wave).toHaveCount(0);
  await mic.click();
  await page.evaluate(()=>window.testSpeech.onerror());
  await expect(wave).toHaveCount(0);
  await expect(mic).toHaveAttribute('aria-pressed','false');
  await mic.click();
  await page.evaluate(()=>window.testSpeech.onend());
  await expect(wave).toHaveCount(0);
  await page.emulateMedia({reducedMotion:'reduce'});
  await mic.click();
  await expect(wave).toBeVisible();
  await expect(page.locator('.voice-wave i').first()).toHaveCSS('animation-name','none');
});

test('choose keyword or semantic text search and preserve mode in filters',async({page})=>{
  await ready(page);
  const query=page.getByRole('textbox',{name:'Tìm kiếm sản phẩm',exact:true});
  const mode=page.getByLabel('Cách tìm kiếm',{exact:true});
  await expect(mode).toHaveValue('keyword');
  await query.fill('túi đựng đồ dùng học tập');
  await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click();
  await expect(page.getByText('Chưa tìm thấy sản phẩm phù hợp.',{exact:false})).toBeVisible();
  await mode.selectOption('semantic');
  await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click();
  await expect(page).toHaveURL(/search_mode=semantic/);
  await expect(page.locator('.product-name').first()).toHaveText('Túi đựng dụng cụ học tập',{timeout:15000});
  await expect(page.getByLabel('Sắp xếp',{exact:true})).toHaveValue('relevance');
  await page.getByRole('button',{name:'Túi',exact:true}).click();
  await expect(page).toHaveURL(/product_type=bag/);
  await expect(mode).toHaveValue('semantic');
  await expect(page.locator('.product-name').first()).toHaveText('Túi đựng dụng cụ học tập');
  await page.reload();
  await expect(mode).toHaveValue('semantic');
  await expect(page.locator('.product-name').first()).toHaveText('Túi đựng dụng cụ học tập');
  await overflow(page);
  await mode.selectOption('keyword');
  await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click();
  await expect(page).toHaveURL(/search_mode=keyword/);
  await expect(page.getByText('Chưa tìm thấy sản phẩm phù hợp.',{exact:false})).toBeVisible();
});

test('semantic service failure offers an explicit keyword fallback',async({page})=>{
  await page.route('**/api/products?**',async route=>{
    if(new URL(route.request().url()).searchParams.get('search_mode')==='semantic')
      await route.fulfill({status:503,json:{error:'Tìm ngữ nghĩa chưa sẵn sàng. Hãy thử lại hoặc chuyển sang tìm từ khóa.',code:503}});
    else await route.continue();
  });
  await ready(page);
  await page.getByLabel('Cách tìm kiếm',{exact:true}).selectOption('semantic');
  await page.getByRole('textbox',{name:'Tìm kiếm sản phẩm',exact:true}).fill('bút');
  await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click();
  await expect(page.getByText('Tìm ngữ nghĩa chưa sẵn sàng.',{exact:false})).toBeVisible();
  await expect(page.locator('.product-card')).toHaveCount(0);
  await page.getByRole('button',{name:'Chuyển sang tìm từ khóa',exact:true}).click();
  await expect(page.getByLabel('Cách tìm kiếm',{exact:true})).toHaveValue('keyword');
  await expect(page.locator('.product-name').first()).toBeVisible();
});

test('semantic search waits for cold initialization beyond fifteen seconds',async({page})=>{
  await page.route('**/api/products?**',async route=>{
    if(new URL(route.request().url()).searchParams.get('search_mode')!=='semantic')return route.continue();
    const response=await route.fetch();
    await new Promise(resolve=>setTimeout(resolve,16000));
    await route.fulfill({response});
  });
  await ready(page);
  await page.getByLabel('Cách tìm kiếm',{exact:true}).selectOption('semantic');
  await page.getByRole('textbox',{name:'Tìm kiếm sản phẩm',exact:true}).fill('túi đựng đồ dùng học tập');
  await page.getByRole('button',{name:'Tìm kiếm',exact:true}).click();
  await expect(page.locator('.product-name').first()).toHaveText('Túi đựng dụng cụ học tập',{timeout:30000});
  await expect(page.getByText('Yêu cầu quá thời gian.',{exact:false})).toHaveCount(0);
});
