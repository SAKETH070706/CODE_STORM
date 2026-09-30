import React,{useEffect,useState} from 'react';

export default function RequestProgress(){
  const [started]=useState(Date.now),[elapsed,setElapsed]=useState(0);
  useEffect(()=>{const timer=setInterval(()=>setElapsed(Math.floor((Date.now()-started)/1000)),1000);return()=>clearInterval(timer);},[started]);
  return <div className="request-progress" role="status">
    <span className="request-spinner" aria-hidden="true"/><div><strong>Waiting for the server{elapsed>0?` · ${elapsed}s`:''}</strong>
    <p>{elapsed>=8?'This is taking longer than usual. Your input is kept; please wait for the result.':'Your request is in progress. Duplicate submissions are disabled.'}</p></div>
  </div>;
}
