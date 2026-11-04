import React,{useId,useState} from 'react';
import {Link} from 'react-router-dom';
import {Package} from 'lucide-react';
import {statuses} from '../../data_infrastructure/http/api';
export function ErrorBox({error}){return error?<p className="error" role="alert">{error}</p>:null;}
export function Empty({children='Chưa có dữ liệu.'}){return <div className="empty"><Package size={36}/><p>{children}</p><Link to="/">Khám phá sản phẩm</Link></div>;}
export function Field({label,children,...props}){const id=useId();return <label className="field"><span id={id}>{label}</span>{children?React.cloneElement(children,{'aria-labelledby':id}):<input {...props} aria-labelledby={id}/>}</label>;}
export function Status({value}){return <span className={'status '+value}>{statuses[value]||value}</span>;}
export function TaskForm({onSubmit,children,submit='Lưu thay đổi',className=''}) {
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  return <form className={'form '+className} onSubmit={async e=>{e.preventDefault();if(busy)return;setBusy(true);setError('');try{await onSubmit(new FormData(e.currentTarget),e.currentTarget);}catch(err){setError(err.message);}finally{setBusy(false);}}}>{children}<ErrorBox error={error}/><button className="primary" disabled={busy}>{busy?'Đang xử lý…':submit}</button></form>;
}

export function LoadingPage({error,reload}){return error?<div className="page"><ErrorBox error={error}/><button onClick={reload}>Thử lại</button></div>:<p className="loading">Đang tải…</p>;}
export function LoginNeeded(){return <div className="page narrow"><h1>Đăng nhập để tiếp tục</h1><p>Xem tài khoản và đơn hàng của bạn tại Mosa.</p><Link className="primary" to="/login">Đăng nhập</Link></div>;}
