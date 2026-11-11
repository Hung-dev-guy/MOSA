let csrf='';
export async function api(path,options={}) {
  const {body,timeoutMs=15000,...rest}=options;
  const form=body instanceof FormData;
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),timeoutMs);
  try {
    const response=await fetch('/api'+path,{...rest,signal:controller.signal,credentials:'same-origin',headers:{...(form?{}:{'Content-Type':'application/json'}),'X-CSRF-Token':csrf,...rest.headers},body:body===undefined?undefined:form?body:JSON.stringify(body)});
    const data=await response.json();
    if(!response.ok) throw new Error(data.error || 'Không thực hiện được. Vui lòng thử lại.');
    if(data.csrf_token) csrf=data.csrf_token;
    return data;
  } catch(error) {
    if(error.name==='AbortError') throw new Error('Yêu cầu quá thời gian. Kiểm tra kết nối và thử lại.');
    if(error instanceof TypeError) throw new Error('Không kết nối được máy chủ. Kiểm tra kết nối và thử lại.');
    throw error;
  } finally {clearTimeout(timer);}
}
export const money=value=>new Intl.NumberFormat('vi-VN',{style:'currency',currency:'VND'}).format(value);
export const date=value=>value?new Date(value).toLocaleString('vi-VN'):'';
export const statuses={PENDING:'Chờ thanh toán',PROCESSING:'Đang xử lý',PAID:'Đã thanh toán',FAILED:'Thất bại',REFUNDED:'Đã hoàn tiền',EMPTY:'Giỏ trống',HAS_ITEMS:'Có sản phẩm',pending:'Chờ thanh toán',confirmed:'Đã xác nhận',payment_failed:'Thanh toán thất bại',cancelled:'Đã huỷ',picking:'Đang lấy hàng',packed:'Đã đóng gói',shipped:'Đã xuất kho',delivered:'Đã giao',success:'Đã thanh toán',failed:'Thất bại',awaiting_collection:'Chờ thu khi nhận',collected:'Đã thu tiền',in_transit:'Đang vận chuyển',exception:'Cần kiểm tra',open:'Mới tiếp nhận',in_progress:'Đang xử lý',closed:'Đã giải quyết'};
