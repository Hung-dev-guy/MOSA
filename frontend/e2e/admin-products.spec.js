import {test,expect} from '@playwright/test';

test('admin searches products and confirms or cancels deletion',async({page},info)=>{
  await page.goto('/login');
  await page.getByLabel('Email',{exact:true}).fill('admin@mosa.local');
  await page.getByLabel('Mật khẩu',{exact:true}).fill('Mosa@12345');
  await page.getByRole('button',{name:'Đăng nhập',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Tài khoản của bạn'})).toBeVisible();
  // Create a disposable product through the API so this test only removes its own record.
  const name='Bút xoá E2E '+info.project.name;
  const product=await page.evaluate(async name=>{
    const session=await (await fetch('/api/session')).json();
    const response=await fetch('/api/staff/products',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token},body:JSON.stringify({name,brand:'MosaTest',product_type:'pen',details:{type:'Gel'},price:15000,selling_unit:'Cây',image:'/assets/pen-blue.png',published:true})});
    if(!response.ok)throw new Error('Could not create disposable test product');
    return response.json();
  },name);
  await page.goto('/staff');
  const search=page.getByRole('searchbox',{name:'Tìm sản phẩm theo tên, mã hoặc thương hiệu'});
  await search.fill('but xoa e2e '+info.project.name);
  const row=page.getByRole('row').filter({hasText:product.id});
  await expect(row).toHaveCount(1);
  await search.fill(product.id);
  await expect(row).toHaveCount(1);
  await search.fill('MosaTest');
  await expect(row).toBeVisible();
  await search.fill('no-matching-product-xyz');
  await expect(page.getByText('Không tìm thấy sản phẩm phù hợp.',{exact:true})).toBeVisible();
  await search.fill(product.id);
  page.once('dialog',dialog=>dialog.dismiss());
  await row.getByRole('button',{name:'Xoá sản phẩm',exact:true}).click();
  await expect(row).toBeVisible();
  page.once('dialog',dialog=>dialog.accept());
  await row.getByRole('button',{name:'Xoá sản phẩm',exact:true}).click();
  await expect(row).toHaveCount(0);
  await expect(page.getByText('Không tìm thấy sản phẩm phù hợp.',{exact:true})).toBeVisible();
});
