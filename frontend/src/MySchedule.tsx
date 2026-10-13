import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import MyProgress from "./MyProgress";
import type { ActionItem, Meeting, Project } from "./types";
const key=(d:Date)=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
export default function MySchedule({userId,projects,actions,meetings,onOpenAction,onOpenMeeting}:{userId:number;projects:Project[];actions:ActionItem[];meetings:Meeting[];onOpenAction:(id:number)=>void;onOpenMeeting:(id:number)=>void}) {
  const today=new Intl.DateTimeFormat("sv-SE",{timeZone:"Asia/Seoul"}).format(new Date());
  const [selected,setSelected]=useState(today);
  const [month,setMonth]=useState(()=>new Date(`${today.slice(0,7)}-01T00:00:00`));
  const [filter,setFilter]=useState("all");
  const personal=(id:number)=>projects.some(p=>p.id===id&&p.workspace_id==null);
  const mine=actions.filter(t=>t.assignee_id===userId||(!t.assignee_id&&personal(t.project_id)));
  const events=[...mine.filter(t=>t.due_date&&t.status!=="cancelled").map(t=>({id:t.id,date:t.due_date!.slice(0,10),title:t.task,type:"task",done:t.status==="done",open:()=>onOpenAction(t.id)})),
    ...meetings.filter(m=>personal(m.project_id)||m.recorder_id===userId).map(m=>({id:m.id,date:m.meeting_date.slice(0,10),title:m.title,type:"meeting",done:false,open:()=>onOpenMeeting(m.id)}))].filter(e=>filter==="all"||e.type===filter);
  const first=new Date(month.getFullYear(),month.getMonth(),1);
  const start=new Date(first);start.setDate(1-first.getDay());
  const days=Array.from({length:42},(_,i)=>{const d=new Date(start);d.setDate(start.getDate()+i);return d;});
  const upcoming=events.filter(e=>e.date>=today).sort((a,b)=>a.date.localeCompare(b.date));
  const shift=(n:number)=>setMonth(new Date(month.getFullYear(),month.getMonth()+n,1));
  return <div className="page my-schedule"><header className="settings-heading"><h2>나의 진행현황 · 일정</h2><p>선택한 공간의 내 담당 업무와 회의 담당 일정을 모았습니다. 개인 프로젝트의 회의도 함께 표시합니다.</p></header>
    <MyProgress tasks={mine} onOpenTask={onOpenAction}/>
    <section className="panel"><div className="calendar-heading"><h2>{month.getFullYear()}년 {month.getMonth()+1}월</h2><div className="workflow-controls"><button className="icon-control" aria-label="이전 달" onClick={()=>shift(-1)}><ChevronLeft/></button><button className="button soft" onClick={()=>{setMonth(new Date(`${today.slice(0,7)}-01T00:00:00`));setSelected(today);}}>오늘</button><button className="icon-control" aria-label="다음 달" onClick={()=>shift(1)}><ChevronRight/></button></div></div>
      <div className="home-tabs" aria-label="일정 종류">{[["all","전체"],["task","업무 마감"],["meeting","회의"]].map(([id,label])=><button key={id} aria-pressed={filter===id} className={filter===id?"active":""} onClick={()=>setFilter(id)}>{label}</button>)}</div>
      <div className="calendar-week">{["일","월","화","수","목","금","토"].map(day=><span key={day}>{day}</span>)}</div>
      <div className="calendar-grid">{days.map(d=>{const date=key(d);const list=events.filter(e=>e.date===date);return <button key={date} className={`calendar-day ${d.getMonth()!==month.getMonth()?"outside":""} ${selected===date?"selected":""}`} aria-label={`${date} 일정 ${list.length}개`} aria-pressed={selected===date} aria-current={date===today?"date":undefined} onClick={()=>setSelected(date)}><b>{d.getDate()}</b><span className="calendar-count">{list.length?`${list.length}개`:""}</span><div className="calendar-dots">{list.slice(0,3).map(e=><i key={`${e.type}-${e.id}`} className={e.type}/>)}</div></button>;})}</div>
      <div className="calendar-legend"><span>● 업무 마감</span><span>● 회의</span></div>
      <h3>{selected} 일정</h3>{events.filter(e=>e.date===selected).map(e=><button className="home-task" key={`${e.type}-${e.id}`} onClick={e.open}><div><b>{e.title}</b><small>{e.type==="task"?"업무 마감":"회의"}{e.done?" · 완료":""}</small></div><span>상세 보기</span></button>)}{!events.some(e=>e.date===selected)&&<p className="home-empty">이 날짜에는 일정이 없습니다.</p>}
    </section>
    <section className="panel"><h2>다가오는 일정</h2>{upcoming.map(e=><button className="home-task" key={`${e.type}-${e.id}`} onClick={e.open}><div><b>{e.title}</b><small>{e.date} · {e.type==="task"?"업무 마감":"회의"}{e.done?" · 완료":""}</small></div></button>)}{!upcoming.length&&<p className="home-empty">다가오는 일정이 없습니다.</p>}<p className="calendar-note">기한이 없는 업무는 위의 나의 진행현황에서 확인하세요. 일정은 업무 마감일과 회의 날짜를 변경하면 함께 반영됩니다.</p></section>
  </div>;
}
