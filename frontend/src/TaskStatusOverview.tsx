import { CheckCircle2, CircleDot, Clock3, XCircle } from "lucide-react";
import StreamlitStatusChart from "./StreamlitStatusChart";
import type { ActionItem } from "./types";
import "./TaskStatusOverview.css";

const groups = [
  { key: "todo", label: "대기", Icon: Clock3 },
  { key: "in_progress", label: "진행 중", Icon: CircleDot },
  { key: "done", label: "완료", Icon: CheckCircle2 },
  { key: "cancelled", label: "취소", Icon: XCircle },
];
const workflowLabels:Record<string,string> = {
  ASSIGNED:"수락 대기", ACCEPTED:"시작 대기", IN_PROGRESS:"진행 중",
  BLOCKED:"차단됨", READY_FOR_REVIEW:"검토 대기", CHANGES_REQUESTED:"수정 요청",
  APPROVED:"최종 완료", CANCELLED:"취소",
};

export default function TaskStatusOverview({tasks,onOpenTask,loading=false}:{tasks:ActionItem[];onOpenTask:(id:number)=>void;loading?:boolean}) {
  if (loading) return <p role="status">업무 상태를 불러오는 중...</p>;
  const grouped = groups.map(group=>({...group,tasks:tasks.filter(task=>task.status===group.key)}));
  return <div className="task-status-overview">
    <div className="task-status-donut"><StreamlitStatusChart groups={grouped.map(g=>({key:g.key,label:g.label,count:g.tasks.length}))}/></div>
    <div className="task-status-board" role="region" aria-label="상태별 업무 보드" tabIndex={0}>
      {grouped.map(({key,label,Icon,tasks:items})=><section className={`task-board-column ${key}`} key={key} aria-label={`${label} 업무 ${items.length}개`}>
        <header><Icon aria-hidden="true"/><h4>{label}</h4><b>{items.length}</b></header>
        <div className="task-board-cards">
          {items.length?items.map(task=><button type="button" className="task-board-card" key={task.id} onClick={()=>onOpenTask(task.id)}>
            <Icon aria-hidden="true"/>
            <span><strong>{task.task}</strong><small>#{task.id} · {task.assignee||"담당자 미지정"}{task.due_date?` · 마감 ${task.due_date}`:""}</small></span>
            <em>{workflowLabels[task.workflow_status||""]||label}</em>
          </button>):<p className="task-board-empty">{label} 업무가 없습니다.</p>}
        </div>
      </section>)}
    </div>
  </div>;
}
