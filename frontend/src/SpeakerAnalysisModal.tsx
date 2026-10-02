import { Check, CheckCircle2, Pencil, X } from "lucide-react";
import { useState } from "react";
import type { ActionItemCandidate, Meeting, SpeakerAnalysis } from "./types";

interface Props {
  meeting:Meeting;
  analysis:SpeakerAnalysis;
  saving:boolean;
  onClose:()=>void;
  onConfirm:(items:ActionItemCandidate[])=>void;
  onSaveSpeakerNames:(speakerNames:Record<string,string>)=>Promise<void>;
}

export default function SpeakerAnalysisModal({meeting,analysis,saving,onClose,onConfirm,onSaveSpeakerNames}:Props) {
  const [items,setItems]=useState(()=>analysis.action_items.map(item=>({...item,selected:true})));
  const [speakerNames,setSpeakerNames]=useState<Record<string,string>>(meeting.speaker_names||{});
  const [editingSpeaker,setEditingSpeaker]=useState<string|null>(null);
  const [speakerDraft,setSpeakerDraft]=useState("");
  const [savingSpeaker,setSavingSpeaker]=useState(false);
  const selected=items.filter(item=>item.selected&&item.task.trim());
  function update(index:number,field:"task"|"assignee"|"due_date"|"priority",value:string){setItems(current=>current.map((item,itemIndex)=>itemIndex===index?{...item,[field]:value||null}:item));}
  function beginSpeakerEdit(speaker:string){setEditingSpeaker(speaker);setSpeakerDraft(speakerNames[speaker]||"");}
  async function saveSpeaker(speaker:string){const next={...speakerNames};const name=speakerDraft.trim();if(name)next[speaker]=name;else delete next[speaker];setSavingSpeaker(true);try{await onSaveSpeakerNames(next);setSpeakerNames(next);if(name)setItems(current=>current.map(item=>item.assignee===speaker?{...item,assignee:name}:item));setEditingSpeaker(null);}finally{setSavingSpeaker(false);}}
  const displayName=(speaker:string)=>speakerNames[speaker]||speaker;
  return <div className="modal-backdrop" onMouseDown={event=>event.target===event.currentTarget&&onClose()}>
    <section className="modal speaker-analysis-modal" role="dialog" aria-modal="true">
      <header><div><span className="kicker">SPEAKER ANALYSIS</span><h2>화자별 쟁점과 후속 업무</h2><small>{meeting.title}</small></div><button className="icon-control" onClick={onClose} title="닫기"><X/></button></header>
      <div className="modal-body speaker-analysis-body">
        <div className="analysis-overview"><section className="analysis-summary"><h3>쟁점 요약</h3><p>{analysis.summary}</p>{analysis.issues.map(issue=><div key={issue}>• {issue}</div>)}</section><aside className="speaker-directory"><h3>화자 이름</h3><p>화자를 눌러 추정 이름을 설정하세요.</p>{analysis.speakers.map(speaker=><div className="speaker-name-row" key={speaker.speaker}>{editingSpeaker===speaker.speaker?<><input autoFocus value={speakerDraft} placeholder="이름 입력" onChange={event=>setSpeakerDraft(event.target.value)} onKeyDown={event=>{if(event.key==="Enter")void saveSpeaker(speaker.speaker);if(event.key==="Escape")setEditingSpeaker(null);}}/><button disabled={savingSpeaker} onClick={()=>void saveSpeaker(speaker.speaker)} title="이름 저장"><Check/></button></>:<button onClick={()=>beginSpeakerEdit(speaker.speaker)}><span><b>{displayName(speaker.speaker)}</b>{speakerNames[speaker.speaker]&&<small>{speaker.speaker}</small>}</span><Pencil/></button>}</div>)}</aside></div>
        <section className="speaker-grid">{analysis.speakers.map(speaker=><article key={speaker.speaker}><b>{displayName(speaker.speaker)}</b>{speakerNames[speaker.speaker]&&<small>{speaker.speaker}</small>}<p>{speaker.stance}</p><ul>{speaker.points.map(point=><li key={point}>{point}</li>)}</ul></article>)}</section>
        <h3>Action Item 후보</h3>
        {items.length?items.map((item,index)=><article className={`candidate ${item.selected?"selected":""}`} key={`${item.task}-${index}`}><label className="candidate-select"><input type="checkbox" checked={item.selected} onChange={event=>setItems(current=>current.map((value,itemIndex)=>itemIndex===index?{...value,selected:event.target.checked}:value))}/><span>업무로 저장</span><b>{Math.round(item.confidence*100)}%</b></label><label>업무<input value={item.task} disabled={!item.selected} onChange={event=>update(index,"task",event.target.value)}/></label><div className="form-grid"><label>담당자<input value={item.assignee||""} disabled={!item.selected} onChange={event=>update(index,"assignee",event.target.value)}/></label><label>기한<input type="date" value={item.due_date||""} disabled={!item.selected} onChange={event=>update(index,"due_date",event.target.value)}/></label><label>우선순위<select value={item.priority} disabled={!item.selected} onChange={event=>update(index,"priority",event.target.value)}><option value="low">낮음</option><option value="medium">보통</option><option value="high">높음</option></select></label></div><blockquote><span>원문 근거</span>{item.evidence}</blockquote></article>):<div className="empty">확인된 후속 업무가 없습니다.</div>}
      </div>
      <footer><span className="selection-count">{selected.length}개 선택</span><button className="button ghost" onClick={onClose}>취소</button><button className="button primary" disabled={!selected.length||saving} onClick={()=>onConfirm(selected)}><CheckCircle2/>{saving?"저장 중...":"Action Item 저장"}</button></footer>
    </section>
  </div>;
}
