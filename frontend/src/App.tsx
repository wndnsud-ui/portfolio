import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Mic, Plus, RefreshCw } from "lucide-react";
import { api } from "./api";
import EntityModal from "./EntityModal";
import DecisionReviewModal from "./DecisionReviewModal";
import { ActionsPage, DashboardPage, DecisionsPage, MeetingsPage, ProjectDetailPage, ProjectsPage } from "./Pages";
import Sidebar from "./Sidebar";
import SettingsPage from "./SettingsPage";
import type { ActionItem, Decision, DecisionCandidate, Entity, EntityType, Meeting, Project, View } from "./types";

const pageNames:Record<View,string>={ dashboard:"대시보드", projects:"프로젝트", meetings:"회의", actions:"Action Items", decisions:"결정사항", settings:"설정" };
const createNames:Record<EntityType,string>={ projects:"새 프로젝트", meetings:"새 회의", actions:"새 업무", decisions:"새 결정" };
const endpoints:Record<EntityType,string>={projects:"/projects",meetings:"/meetings",actions:"/action-items",decisions:"/decisions"};

export default function App() {
  const [view,setView]=useState<View>("dashboard");
  const [modal,setModal]=useState<{type:EntityType;item:Entity|null;defaults?:Record<string,string|number>}|null>(null);
  const [projectTarget,setProjectTarget]=useState<{projectId:number;meetingId?:number;actionId?:number;decisionId?:number}|null>(null);
  const [sidebarOpen,setSidebarOpen]=useState(false);
  const [toast,setToast]=useState("");
  const [review,setReview]=useState<{meeting:Meeting;candidates:DecisionCandidate[]}|null>(null);
  const [reviewingId,setReviewingId]=useState<number|null>(null);
  const [summarizingId,setSummarizingId]=useState<number|null>(null);
  const [savingReview,setSavingReview]=useState(false);
  const queryClient=useQueryClient();
  const projects=useQuery({queryKey:["projects"],queryFn:()=>api<Project[]>("/projects")});
  const meetings=useQuery({queryKey:["meetings"],queryFn:()=>api<Meeting[]>("/meetings")});
  const actions=useQuery({queryKey:["actions"],queryFn:()=>api<ActionItem[]>("/action-items")});
  const decisions=useQuery({queryKey:["decisions",projects.data?.map(value=>value.id)],enabled:Boolean(projects.data),queryFn:async()=>{const sets=await Promise.all((projects.data||[]).map(project=>api<Decision[]>(`/projects/${project.id}/decisions`)));return sets.flat();}});
  const data={projects:projects.data||[],meetings:meetings.data||[],actions:actions.data||[],decisions:decisions.data||[]};
  const loading=[projects,meetings,actions,decisions].some(query=>query.isLoading);
  function notify(message:string){setToast(message);window.setTimeout(()=>setToast(""),2600);}
  async function refresh(){await queryClient.invalidateQueries();notify("새로고침했습니다.");}

  const remove=useMutation({mutationFn:({type,id}:{type:EntityType;id:number})=>api(`${endpoints[type]}/${id}`,{method:"DELETE"}),onSuccess:async()=>{await queryClient.invalidateQueries();notify("삭제했습니다.");}});
  async function onDelete(type:EntityType,id:number){if(window.confirm("이 항목을 삭제할까요?"))remove.mutate({type,id});}
  async function onEdit(type:EntityType,id:number){let item=(data[type] as Entity[]).find(value=>value.id===id)||null;if(type==="meetings")item=await api<Meeting>(`/meetings/${id}`);setModal({type,item});}
  async function onSave(payload:Record<string,unknown>){if(!modal)return;const id=modal.item?.id;await api(`${endpoints[modal.type]}${id?`/${id}`:""}`,{method:id?"PATCH":"POST",body:JSON.stringify(payload)});setModal(null);await queryClient.invalidateQueries();notify(id?"수정했습니다.":"저장했습니다.");}
  async function onNotion(id:number){try{const result=await api<{status:string}>(`/meetings/${id}/notion-sync`,{method:"POST"});await queryClient.invalidateQueries({queryKey:["meetings"]});notify(result.status==="ALREADY_SYNCED"?"이미 Notion에 동기화됐습니다.":"Notion에 전송했습니다.");}catch(error){notify(error instanceof Error?error.message:"Notion 전송에 실패했습니다.");}}
  async function onReview(id:number){setReviewingId(id);try{const meeting=await api<Meeting>(`/meetings/${id}`);const result=await api<{meeting_id:number;candidates:DecisionCandidate[]}>(`/meetings/${id}/decision-candidates`,{method:"POST"});setReview({meeting,candidates:result.candidates});}catch(error){notify(error instanceof Error?error.message:"결정사항 분석에 실패했습니다.");}finally{setReviewingId(null);}}
  async function onSummarize(id:number){setSummarizingId(id);try{await api<Meeting>(`/meetings/${id}/summarize`,{method:"POST"});await queryClient.invalidateQueries({queryKey:["meetings"]});await queryClient.invalidateQueries({queryKey:["project-meeting-details"]});notify("쟁점 중심 요약을 저장했습니다.");}catch(error){notify(error instanceof Error?error.message:"회의 요약에 실패했습니다.");}finally{setSummarizingId(null);}}
  async function onConfirm(items:DecisionCandidate[]){if(!review)return;setSavingReview(true);try{await api(`/meetings/${review.meeting.id}/decisions/confirm`,{method:"POST",body:JSON.stringify({decisions:items.map(({topic,value})=>({topic,value}))})});await queryClient.invalidateQueries({queryKey:["decisions"]});setReview(null);notify(`${items.length}개 결정사항을 확정했습니다.`);}catch(error){notify(error instanceof Error?error.message:"결정사항 저장에 실패했습니다.");}finally{setSavingReview(false);}}
  function openProject(id:number){setProjectTarget({projectId:id});setView("projects");}
  function openMeeting(id:number){const meeting=data.meetings.find(item=>item.id===id);if(meeting){setProjectTarget({projectId:meeting.project_id,meetingId:id});setView("projects");}}
  function openAction(id:number){const action=data.actions.find(item=>item.id===id);if(action){setProjectTarget({projectId:action.project_id,meetingId:action.meeting_id||undefined,actionId:id});setView("projects");}}
  function openDecision(id:number){const decision=data.decisions.find(item=>item.id===id);if(decision){setProjectTarget({projectId:decision.project_id,meetingId:decision.meeting_id||undefined,decisionId:id});setView("projects");}}
  function createAction(projectId:number,meetingId?:number){setModal({type:"actions",item:null,defaults:{project_id:projectId,...(meetingId?{meeting_id:meetingId}:{})}});}
  const common={...data,onEdit,onDelete,onNotion,onReview,reviewingId,onSummarize,summarizingId,onOpenProject:openProject,onOpenMeeting:openMeeting,onOpenAction:openAction,onOpenDecision:openDecision,onCreateAction:createAction};
  const Current={dashboard:DashboardPage,projects:ProjectsPage,meetings:MeetingsPage,actions:ActionsPage,decisions:DecisionsPage}[view as Exclude<View,"settings">];
  function create(type?:EntityType){const target=type||(view==="dashboard"?"projects":view as EntityType);if(target!=="projects"&&!data.projects.length){notify("프로젝트를 먼저 만들어 주세요.");setView("projects");return;}setModal({type:target,item:null});}
  const selectedProject=data.projects.find(project=>project.id===projectTarget?.projectId);
  return <div className="app-shell">
    <Sidebar view={view} open={sidebarOpen} onToggle={()=>setSidebarOpen(value=>!value)} onChange={next=>{setView(next);setProjectTarget(null);setSidebarOpen(false);}}/>
    <main className="main-content">
      <header className="topbar"><div><span className="kicker">WORKSPACE</span><h1>{pageNames[view]}</h1></div>{view!=="settings"&&<div className="top-actions"><button className="icon-control desktop-only" onClick={refresh} title="새로고침"><RefreshCw/></button><button className="button soft" onClick={()=>create("meetings")}><Mic/>음성 회의</button><button className="button primary" onClick={()=>create()}><Plus/>{createNames[view==="dashboard"?"projects":view as EntityType]}</button></div>}</header>
      {view==="settings"?<SettingsPage onNotify={notify}/>:loading?<div className="loading">데이터를 불러오는 중...</div>:selectedProject?<ProjectDetailPage {...common} project={selectedProject} target={projectTarget||undefined} onBack={()=>setProjectTarget(null)}/>:<Current {...common}/>} 
    </main>
    {modal&&<EntityModal {...modal} projects={data.projects} onClose={()=>setModal(null)} onSave={onSave}/>} 
    {review&&<DecisionReviewModal meeting={review.meeting} candidates={review.candidates} saving={savingReview} onClose={()=>setReview(null)} onConfirm={onConfirm}/>} 
    {toast&&<div className="toast">{toast}</div>}
  </div>;
}
