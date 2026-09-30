import {createContext,createElement} from 'react';
export const RequestContext=createContext(false);
export const pretty=value=>JSON.stringify(value,null,2);
export const options=rows=>(rows||[]).map(r=>createElement('option',{key:r.id,value:r.id},r.name||r.id));
