import { useEffect, useState } from "react";
import { Edit3, Eye, X } from "lucide-react";
import AudioRecorder from "./AudioRecorder";
import MarkdownContent from "./MarkdownContent";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type { ActionItem, Decision, Entity, EntityType, Meeting, Project } from "./types";

interface Props { type:EntityType; item:Entity | null; defaults?:Record<string,string|number>; projects:Project[]; onClose:()=>void; onSave:(payload:Record<string, unknown>)=>Promise<void>; }
const titles = { projects:"프로젝트", meetings:"회의", actions:"Action Item", decisions:"결정사항" };

export default function EntityModal({ type, item, defaults={}, projects, onClose, onSave }: Props) {
  const [data, setData] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const members=useQuery({queryKey:["project-members",Number(data.project_id)],enabled:!!data.project_id,staleTime:0,refetchOnMount:"always",queryFn:()=>api<{user_id:number;nickname:string|null;email:string}[]>(`/projects/${data.project_id}/members`)});
  const [saving, setSaving] = useState(false);
  const [transcriptTab,setTranscriptTab]=useState<"write"|"preview">("write");
  useEffect(() => {
    if (type === "projects") { const value=item as Project|null; setData({name:value?.name||"",description:value?.description||""}); }
    if (type === "meetings") { const value=item as Meeting|null; setData({project_id:String(value?.project_id||defaults.project_id||projects[0]?.id||""),title:value?.title||"",meeting_date:value?.meeting_date||new Date().toISOString().slice(0,10),participants:value?.participants.join(", ")||"",speaker_names:Object.entries(value?.speaker_names||{}).map(([speaker,name])=>`${speaker}=${name}`).join(", "),recorder_id:String(value?.recorder_id||""),transcript:value?.transcript||""}); }
    if (type === "actions") { const value=item as ActionItem|null; setData({project_id:String(value?.project_id||defaults.project_id||projects[0]?.id||""),meeting_id:String(value?.meeting_id||defaults.meeting_id||""),task:value?.task||"",assignee_id:String(value?.assignee_id||""),description:value?.description||"",assignee:value?.assignee||"",due_date:value?.due_date||"",status:value?.status||"todo",priority:value?.priority||"medium"}); }
    if (type === "decisions") { const value=item as Decision|null; setData({project_id:String(value?.project_id||""),topic:value?.topic||"",value:value?.value||"",status:value?.status||"draft"}); }
  }, [type, item, defaults.project_id, defaults.meeting_id, projects[0]?.id]);
  const field = (name:string) => ({ value:data[name]||"", onChange:(event:React.ChangeEvent<HTMLInputElement|HTMLTextAreaElement|HTMLSelectElement>) => setData(current=>({...current,[name]:event.target.value,...(name==="project_id"?{assignee_id:"",recorder_id:"",meeting_id:""}:{})})) });
  async function submit(event:React.FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    let payload:Record<string, unknown> = {...data};
    if (!item && "project_id" in payload) payload.project_id = Number(payload.project_id);
    else if (item) delete payload.project_id;
    if (type === "meetings") { payload.recorder_id=data.recorder_id?Number(data.recorder_id):null;if(item&&(item as Meeting).recorder_id===payload.recorder_id)delete payload.recorder_id; payload.participants = data.participants.split(",").map(value=>value.trim()).filter(Boolean); payload.speaker_names=Object.fromEntries(data.speaker_names.split(",").map(value=>value.split("=").map(part=>part.trim())).filter(parts=>parts.length===2&&parts[0]&&parts[1])); }
    if (type === "actions") { payload.assignee_id=data.assignee_id?Number(data.assignee_id):null;if(data.assignee_id||((item as ActionItem|null)?.workflow_status))delete payload.status;payload.assignee=data.assignee||null; payload.due_date=data.due_date||null; payload.meeting_id=data.meeting_id?Number(data.meeting_id):null; }
    try { await onSave(payload); } catch (reason) { setError(reason instanceof Error ? reason.message : "저장하지 못했습니다."); setSaving(false); }
  }
  return <div className="modal-backdrop" onMouseDown={event => { if(event.target===event.currentTarget) onClose(); }}><form className="modal" onSubmit={submit}>
    <header><div><span className="kicker">{item ? "EDIT" : "CREATE"}</span><h2>{item ? "수정" : "새"} {titles[type]}</h2></div><button type="button" className="icon-control" onClick={onClose} title="닫기"><X/></button></header>
    <div className="modal-body">
      {type !== "projects" && <label>프로젝트<select required disabled={Boolean(item)} {...field("project_id")}><option value="">선택하세요</option>{projects.map(project=><option key={project.id} value={project.id}>{project.name}</option>)}</select></label>}
      {type === "projects" && <><label>프로젝트명<input required {...field("name")}/></label><label>설명<textarea {...field("description")}/></label></>}
      {type === "meetings" && <><label>회의 제목<input required {...field("title")}/></label><div className="form-grid"><label>회의 날짜<input type="date" required {...field("meeting_date")}/></label><label>참석자<input placeholder="쉼표로 구분" {...field("participants")}/></label></div><label>회의록 담당자<select {...field("recorder_id")}><option value="">미지정</option>{members.data?.map(m=><option key={m.user_id} value={m.user_id}>{m.nickname||m.email}</option>)}</select></label><label>TXT · MD 원문 업로드<input type="file" accept=".txt,.md" onChange={async e=>{const file=e.target.files?.[0];if(file){if(file.size>2*1024*1024){setError("텍스트 파일은 최대 2MB입니다.");return;}const text=await file.text();setData(current=>({...current,transcript:text}));}e.target.value="";}}/></label><label>화자 이름 매핑<input placeholder="화자 1=혜영, 화자 2=민수" {...field("speaker_names")}/><small>회의 관리자가 추정 이름을 직접 수정할 수 있습니다.</small></label><label>실시간 녹음 및 음성 전사<AudioRecorder onTranscript={text=>setData(current=>({...current,transcript:text}))} onError={setError}/></label><div className="transcript-editor"><div className="editor-heading"><span>회의 원문</span><div className="editor-tabs"><button type="button" className={transcriptTab==="write"?"active":""} onClick={()=>setTranscriptTab("write")}><Edit3/>작성</button><button type="button" className={transcriptTab==="preview"?"active":""} onClick={()=>setTranscriptTab("preview")}><Eye/>미리보기</button></div></div>{transcriptTab==="write"?<textarea className="transcript" aria-label="회의 원문" {...field("transcript")}/>:<MarkdownContent content={data.transcript||"*내용이 없습니다.*"} className="markdown-preview"/>}</div></>}
      {type === "actions" && <><label>설명<textarea {...field("description")}/></label><label>업무<input required {...field("task")}/></label><div className="form-grid"><label>담당자<select disabled={!data.project_id||members.isFetching||members.isError} {...field("assignee_id")}><option value="">{!data.project_id?"프로젝트를 먼저 선택하세요":members.isFetching?"팀원 불러오는 중...":"미배정"}</option>{members.data?.map(m=><option key={m.user_id} value={m.user_id}>{m.nickname||m.email}</option>)}</select></label><label>기한<input type="date" {...field("due_date")}/></label><label>상태<select disabled={!!data.assignee_id||!!(item as ActionItem|null)?.workflow_status} {...field("status")}><option value="todo">할 일</option><option value="in_progress">진행 중</option><option value="done">완료</option><option value="cancelled">취소</option></select></label>{members.isError&&<p role="alert">{members.error.message}</p>}<label>우선순위<select {...field("priority")}><option value="low">낮음</option><option value="medium">보통</option><option value="high">높음</option></select></label></div></>}
      {type === "decisions" && <><label>주제<input required {...field("topic")}/></label><label>결정 내용<textarea required {...field("value")}/></label><label>상태<select disabled={!!data.assignee_id||!!(item as ActionItem|null)?.workflow_status} {...field("status")}><option value="draft">초안</option><option value="confirmed">확정</option></select></label></>}
      {error && <p className="form-error">{error}</p>}
    </div>
    <footer><button type="button" className="button ghost" onClick={onClose}>취소</button><button className="button primary" disabled={saving}>{saving ? "저장 중" : "저장"}</button></footer>
  </form></div>;
}
