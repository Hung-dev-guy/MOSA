import React,{useEffect,useState} from 'react';
import {Link,Route,Routes,useLocation} from 'react-router-dom';
import {Check,X} from 'lucide-react';
import {api} from '../data_infrastructure/http/api';
import {Store} from './shared/store';
import {Empty,ErrorBox} from './shared/components';
import Staff from './admin_staff_ui/AdminStaffUI';
import {Header,Catalogue,ProductPage,CartPage,Checkout,Auth,Recovery,Account,Orders,OrderPage,Payment,Support,Footer} from './customer_ui/CustomerUI';
export default function App(){
  const [session,setSession]=useState(null),[productTypes,setProductTypes]=useState([]),[cart,setCart]=useState({items:[],subtotal:0}),[toast,setToast]=useState(''),[bootError,setBootError]=useState('');
  const location=useLocation();
  const [imageFile,setImageFile]=useState(null);
  const refreshCart=async()=>setCart(await api('/cart'));
  const refreshSession=async()=>setSession(await api('/session'));
  const boot=async()=>{try{setBootError('');const s=await api('/session');setSession(s);setProductTypes(await api('/product-types'));await refreshCart();}catch(e){setBootError(e.message);}};
  useEffect(()=>{boot();},[]);
  useEffect(()=>{window.scrollTo(0,0);},[location.pathname]);
  useEffect(()=>{if(!toast)return;const t=setTimeout(()=>setToast(''),4000);return()=>clearTimeout(t);},[toast]);
  const add=async(id,quantity=1)=>{await api('/cart/items',{method:'POST',body:{product_id:id,quantity}});await refreshCart();setToast('Đã thêm sản phẩm vào giỏ hàng.');};
  if(!session)return <div className="boot"><h1>mosa<span>.</span></h1>{bootError?<><ErrorBox error={bootError}/><button onClick={boot}>Thử lại</button></>:<p>Đang mở cửa hàng…</p>}</div>;
  return <Store.Provider value={{session,setSession,productTypes,cart,refreshCart,refreshSession,add,notify:setToast}}><Header imageFile={imageFile} onImageSelect={setImageFile}/><main className="shell"><Routes>
    <Route path="/" element={<Catalogue imageFile={imageFile}/>}/><Route path="/product/:id" element={<ProductPage/>}/><Route path="/cart" element={<CartPage/>}/><Route path="/checkout" element={<Checkout/>}/><Route path="/login" element={<Auth/>}/><Route path="/register" element={<Auth register/>}/><Route path="/recovery" element={<Recovery/>}/><Route path="/reset" element={<Recovery reset/>}/><Route path="/account" element={<Account/>}/><Route path="/orders" element={<Orders/>}/><Route path="/orders/:id" element={<OrderPage/>}/><Route path="/payment/:id" element={<Payment/>}/><Route path="/support" element={<Support/>}/><Route path="/staff" element={<Staff/>}/><Route path="*" element={<Empty>Không tìm thấy trang.</Empty>}/>
  </Routes></main><Footer/>{toast&&<div className="toast" role="status"><Check size={20}/>{toast}<button aria-label="Đóng thông báo" onClick={()=>setToast('')}><X size={17}/></button></div>}</Store.Provider>;
}
