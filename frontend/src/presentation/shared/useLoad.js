import {useEffect,useState} from 'react';
import {api} from '../../data_infrastructure/http/api';
export function useLoad(path){const [data,setData]=useState(null),[error,setError]=useState(''),[revision,setRevision]=useState(0);useEffect(()=>{let live=true;setError('');api(path).then(d=>{if(live)setData(d);}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[path,revision]);return {data,error,reload:()=>setRevision(x=>x+1)};}
