import {useEffect, useRef, useMemo} from 'react';
import {RequestError} from '../workspaceClient';

// Synchronous gate prevents double submissions before React paints a disabled button.
export default function useRequest() {
  const state=useRef({controller:null,alive:true});
  useEffect(()=>{const s=state.current;s.alive=true;return()=>{s.alive=false;s.controller?.abort();s.controller=null;};},[]);
  return useMemo(()=>({
    begin(){const s=state.current;if(s.controller)return null;s.controller=new AbortController();return s.controller.signal;},
    finish(signal){if(state.current.controller?.signal!==signal)return false;state.current.controller=null;return state.current.alive;},
    async call(signal,fn){const result=await fn(signal);if(!state.current.alive||signal.aborted)throw new RequestError('Request cancelled.',{code:'CANCELLED'});return result;},
    active(){return state.current.alive;},
  }),[]);
}
