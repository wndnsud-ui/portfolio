import { CheckCircle2, X } from "lucide-react";
import { useState } from "react";
import type { DecisionCandidate, Meeting } from "./types";

interface Props { meeting:Meeting; candidates:DecisionCandidate[]; saving:boolean; onClose:()=>void; onConfirm:(items:DecisionCandidate[])=>void; }

export default function DecisionReviewModal({meeting,candidates,saving,onClose,onConfirm}:Props) {
  const [items,setItems]=useState(()=>candidates.map(candidate=>({...candidate,selected:true})));
  const selected=items.filter(item=>item.selected&&item.topic.trim()&&item.value.trim());
  function update(index:number,field:"topic"|"value",value:string){setItems(current=>current.map((item,itemIndex)=>itemIndex===index?{...item,[field]:value}:item));}
  return <div className="modal-backdrop" role="presentation" onMouseDown={event=>event.target===event.currentTarget&&onClose()}>
    <section className="modal review-modal" role="dialog" aria-modal="true" aria-labelledby="review-title">
      <header><div><span className="kicker">AI REVIEW</span><h2 id="review-title">결정사항 검토</h2><small>{meeting.title}</small></div><button className="icon-control" onClick={onClose} title="닫기"><X/></button></header>
      <div className="modal-body review-body">
        {items.length?items.map((item,index)=><article className={`candidate ${item.selected?"selected":""}`} key={`${item.topic}-${index}`}>
          <label className="candidate-select"><input type="checkbox" checked={item.selected} onChange={event=>setItems(current=>current.map((value,itemIndex)=>itemIndex===index?{...value,selected:event.target.checked}:value))}/><span>확정 대상</span><b>{Math.round(item.confidence*100)}%</b></label>
          <label>결정 주제<input value={item.topic} onChange={event=>update(index,"topic",event.target.value)} disabled={!item.selected}/></label>
          <label>확정 내용<textarea value={item.value} onChange={event=>update(index,"value",event.target.value)} disabled={!item.selected}/></label>
          <blockquote><span>원문 근거</span>{item.evidence}</blockquote>
        </article>):<div className="empty review-empty"><CheckCircle2/><b>확정할 결정사항이 없습니다.</b><span>명시적으로 합의된 문장이 회의록에서 발견되지 않았습니다.</span></div>}
      </div>
      <footer><span className="selection-count">{selected.length}개 선택</span><button className="button ghost" onClick={onClose}>취소</button><button className="button primary" disabled={!selected.length||saving} onClick={()=>onConfirm(selected)}><CheckCircle2/>{saving?"저장 중...":"선택 항목 확정"}</button></footer>
    </section>
  </div>;
}
