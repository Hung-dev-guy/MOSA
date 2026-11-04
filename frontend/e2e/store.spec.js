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

test('guest cart, register, checkout promo, payment and personal order',async({page},info)=>{
  await ready(page,'/product/3');
  await page.getByRole('button',{name:'Thêm vào giỏ hàng',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Đã thêm');
  await ready(page,'/cart');
  await expect(page.getByText('Giấy in Double A A4 80gsm',{exact:true})).toBeVisible();
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
  await page.getByLabel('Mã giảm giá',{exact:true}).fill('BADCODE');
  await page.getByRole('button',{name:'Áp dụng',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Mã giảm giá không hợp lệ');
  await page.getByLabel('Mã giảm giá',{exact:true}).fill('MOSA10');
  await page.getByRole('button',{name:'Áp dụng',exact:true}).click();
  await expect(page.locator('.summary-total')).toContainText('105.100');
  await page.getByLabel('Thanh toán trực tuyến mô phỏng',{exact:false}).check();
  await overflow(page);
  await page.getByRole('button',{name:'Xác nhận đặt hàng',exact:true}).click();
  await expect(page.getByText('MÔ PHỎNG THANH TOÁN',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Ghi nhận kết quả mô phỏng',exact:true}).click();
  await expect(page.getByRole('heading',{name:/Đơn hàng MOSA-/})).toBeVisible();
  await expect(page.locator('.status.success')).toContainText('Đã thanh toán');
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
  await expect(page.getByRole('heading',{name:'Kết quả cho “bút xanh”'})).toBeVisible();
  await ready(page,'/?image=1');
  await page.getByLabel('Chọn ảnh tìm sản phẩm').setInputFiles(path.resolve('public/assets/pen-blue.png'));
  await expect(page.getByText('So khớp màu và bố cục;',{exact:false})).toBeVisible();
  await expect(page.locator('.product-name').first()).toContainText('Bút gel Thiên Long');
});

test('admin catalogue, stock and report workspace',async({page},info)=>{
  await login(page,'admin');
  await page.getByRole('link',{name:/Mở khu vực quản trị/}).click();
  await expect(page.getByRole('heading',{name:'Quản lý cửa hàng'})).toBeVisible();
  const first=page.getByRole('row').filter({hasText:'#1 Bút gel'});
  await first.getByRole('button',{name:'Chỉnh sửa'}).click();
  await page.getByLabel('Giá VND',{exact:true}).fill('12000');
  await page.getByRole('button',{name:'Cập nhật sản phẩm',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Đã lưu thay đổi');
  await page.getByRole('tab',{name:'Tồn kho',exact:true}).click();
  await page.getByLabel('Sản phẩm',{exact:true}).selectOption('1');
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
