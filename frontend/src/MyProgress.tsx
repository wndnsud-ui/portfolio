import type { ActionItem } from "./types";

const states:Record<string,string>={ASSIGNED:"수락 대기",ACCEPTED:"시작 대기",IN_PROGRESS:"진행 중",BLOCKED:"진행 보류",READY_FOR_REVIEW:"검토 대기",CHANGES_REQUESTED:"수정 요청",APPROVED:"완료",todo:"시작 대기",in_progress:"진행 중",done:"완료"};
export default function MyProgress({tasks,onOpenTask}:{tasks:ActionItem[];onOpenTask:(id:number)=>void}) {
  const active=tasks.filter(t=>t.status!=="cancelled"&&t.workflow_status!=="CANCELLED");
  const completed=(t:ActionItem)=>t.workflow_status==="APPROVED"||(!t.workflow_status&&t.status==="done");
  const done=active.filter(completed).length;
  const pending=active.filter(t=>!completed(t)).sort((a,b)=>(a.due_date||"9999").localeCompare(b.due_date||"9999"));
  const percent=active.length?Math.round(done/active.length*100):0;
  return <section className="panel my-progress" aria-label="나의 진행현황"><header className="home-panel-head"><h2>나의 진행현황</h2><span>{done}/{active.length}개 완료</span></header>
    <div className="my-progress-summary"><strong>{percent}%</strong><div><span>내 업무 완료율</span><progress aria-label="내 업무 완료율" value={percent} max={100}/></div></div>
    {!active.length?<p className="home-empty">아직 내 담당 업무가 없습니다.</p>:!pending.length?<p className="home-empty">모든 업무를 완료했습니다.</p>:pending.map(t=><button key={t.id} className="my-progress-task" onClick={()=>onOpenTask(t.id)}><div><b>{t.task}</b><small>{t.due_date?`마감 ${t.due_date.slice(0,10)}`:"기한 미정"} · {states[t.workflow_status||t.status]||"진행 중"}</small></div><span>{t.progress_percent==null?"진행률 미입력":`${t.progress_percent}%`}</span>{t.progress_percent!=null&&<progress aria-label={`${t.task} 진행률`} value={t.progress_percent} max={100}/>} {t.progress_content&&<p>{t.progress_content}</p>}</button>)}
  </section>;
}
