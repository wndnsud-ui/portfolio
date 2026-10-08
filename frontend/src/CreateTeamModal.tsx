import { useEffect, useState } from "react";
import { Users, X } from "lucide-react";
import { api } from "./api";
import type { Workspace } from "./types";

export default function CreateTeamModal({onClose,onCreated}:{onClose:()=>void;onCreated:(team:Workspace)=>void}) {
  const [name,setName]=useState("");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  useEffect(()=>{const close=(e:KeyboardEvent)=>{if(e.key==="Escape"&&!busy)onClose();};window.addEventListener("keydown",close);return()=>window.removeEventListener("keydown",close);},[busy,onClose]);
  async function submit(e:React.FormEvent){
    e.preventDefault();if(!name.trim()||busy)return;setBusy(true);setError("");
    try{const team=await api<Workspace>("/workspaces",{method:"POST",body:JSON.stringify({name:name.trim()})});onCreated(team);}
    catch(e){setError(e instanceof Error?e.message:"팀을 만들지 못했습니다.");setBusy(false);}
  }
  return <div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="create-team-title" style={{maxWidth:480}}>
    <header><h2 id="create-team-title"><Users size={20}/> 팀 만들기</h2><button type="button" className="icon-control" title="닫기" disabled={busy} onClick={onClose}><X/></button></header>
    <form onSubmit={submit}><div className="modal-body"><p>팀을 만들면 팀장으로 팀원 초대, 업무 배정과 결과 승인을 할 수 있습니다.</p><label>팀 이름<input autoFocus required maxLength={200} placeholder="예: 서비스 개발팀" value={name} disabled={busy} onChange={e=>setName(e.target.value)}/></label>{error&&<p className="form-error" role="alert">{error}</p>}</div><footer><button type="button" className="button ghost" disabled={busy} onClick={onClose}>취소</button><button className="button primary" disabled={busy||!name.trim()}>{busy?"만드는 중...":"팀 만들기"}</button></footer></form>
  </section></div>;
}
