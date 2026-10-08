import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type { Project, View } from "./types";

export default function GettingStartedGuide(_props:{project:Project;onNavigate:(view:View)=>void;onOpenProject:(id:number)=>void}) {
  const qc=useQueryClient();const [busy,setBusy]=useState(false);const [error,setError]=useState("");
  async function remove(){
    if(!window.confirm("예시 프로젝트와 그 안의 회의·업무·결과를 모두 삭제할까요? 예시 프로젝트에 직접 추가한 내용도 삭제됩니다. 다른 프로젝트는 유지됩니다."))return;
    setBusy(true);setError("");
    try{await api("/auth/example-data",{method:"DELETE"});await qc.invalidateQueries();}
    catch(e){setError(e instanceof Error?e.message:"예시를 삭제하지 못했습니다.");setBusy(false);}
  }
  return <section className="panel getting-started-guide" aria-label="처음 사용자 가이드">
    <h2>이전 예시 데이터가 남아 있습니다</h2>
    <p>사용 안내는 상단 ‘튜토리얼 보기’에서 확인하세요. 필요 없는 예시 프로젝트는 삭제할 수 있습니다.</p>
    <button className="button ghost" disabled={busy} onClick={()=>void remove()}>{busy?"삭제 중...":"예시 데이터 삭제"}</button>
    {error&&<p role="alert">{error}</p>}
  </section>;
}
