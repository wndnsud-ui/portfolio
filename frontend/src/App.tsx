import { lazy, Suspense, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LogOut, Plus, RefreshCw, UserRound } from "lucide-react";
import { api } from "./api";
import AuthPage from "./AuthPage";
import EntityModal from "./EntityModal";
import DecisionReviewModal from "./DecisionReviewModal";
import { ActionsPage, DecisionsPage, MeetingsPage, ProjectDetailPage, ProjectsPage } from "./Pages";
import Sidebar from "./Sidebar";
import HomeDashboard from "./HomeDashboard";
import SettingsPage from "./SettingsPage";
const WorkflowPage=lazy(()=>import("./WorkflowPage"));
import type { Workspace } from "./types";
import SpeakerAnalysisModal from "./SpeakerAnalysisModal";
import type { ActionItem, ActionItemCandidate, AuthUser, Decision, DecisionCandidate, Entity, EntityType, Meeting, Project, SpeakerAnalysis, View } from "./types";

const pageNames:Record<View,string>={ dashboard:"홈", projects:"프로젝트", meetings:"회의", actions:"업무 관리", decisions:"결정사항", settings:"설정", workflow:"검토 · 결재 · 알림" };
const createNames:Record<EntityType,string>={ projects:"새 프로젝트", meetings:"새 회의", actions:"새 업무", decisions:"새 결정" };
const endpoints:Record<EntityType,string>={projects:"/projects",meetings:"/meetings",actions:"/action-items",decisions:"/decisions"};

export default function App() {
  const [view,setView]=useState<View>("dashboard");
  const [workspaceId,setWorkspaceId]=useState<number|null>(null);
  const [modal,setModal]=useState<{type:EntityType;item:Entity|null;defaults?:Record<string,string|number>}|null>(null);
  const [projectTarget,setProjectTarget]=useState<{projectId:number;meetingId?:number;actionId?:number;decisionId?:number}|null>(null);
  const [sidebarOpen,setSidebarOpen]=useState(false);
  const [toast,setToast]=useState("");
  const [authenticated,setAuthenticated]=useState(Boolean(localStorage.getItem("decisionflow_token")));
  const [user,setUser]=useState<AuthUser|null>(null);
  const [authChecking,setAuthChecking]=useState(Boolean(localStorage.getItem("decisionflow_token")));
  const [onboarding,setOnboarding]=useState(false);
  const [review,setReview]=useState<{meeting:Meeting;candidates:DecisionCandidate[]}|null>(null);
  const [reviewingId,setReviewingId]=useState<number|null>(null);
  const [summarizingId,setSummarizingId]=useState<number|null>(null);
  const [savingReview,setSavingReview]=useState(false);
  const [speakerReview,setSpeakerReview]=useState<{meeting:Meeting;analysis:SpeakerAnalysis}|null>(null);
  const [analyzingSpeakersId,setAnalyzingSpeakersId]=useState<number|null>(null);
  const [savingActions,setSavingActions]=useState(false);
  const queryClient=useQueryClient();
  const canLoadData=authenticated&&Boolean(user);
  const workspaces=useQuery({queryKey:["workspaces",user?.id],enabled:canLoadData,queryFn:()=>api<Workspace[]>("/workspaces")});
  useEffect(()=>{if(workspaces.data?.length&&(workspaceId===null||(workspaceId!==0&&!workspaces.data.some(w=>w.id===workspaceId))))setWorkspaceId(workspaces.data[0].id);},[workspaces.data,workspaceId]);
  const workspace=workspaces.data?.find(w=>w.id===workspaceId)||null;
  function selectWorkspace(id:number){setWorkspaceId(id);setProjectTarget(null);setModal(null);setReview(null);setSpeakerReview(null);setView("dashboard");}

  const projects=useQuery({queryKey:["projects",user?.id],enabled:canLoadData,queryFn:()=>api<Project[]>("/projects")});
  const meetings=useQuery({queryKey:["meetings",user?.id],enabled:canLoadData,queryFn:()=>api<Meeting[]>("/meetings")});
  const actions=useQuery({queryKey:["actions",user?.id],enabled:canLoadData,queryFn:()=>api<ActionItem[]>("/action-items")});
  const decisions=useQuery({queryKey:["decisions",user?.id,projects.data?.map(value=>value.id)],enabled:canLoadData&&Boolean(projects.data),queryFn:async()=>{const sets=await Promise.all((projects.data||[]).map(project=>api<Decision[]>(`/projects/${project.id}/decisions`)));return sets.flat();}});
  const scopedProjects=(projects.data||[]).filter(p=>workspaceId===null||(workspaceId===0?p.workspace_id==null:p.workspace_id===workspaceId));
  const scopedIds=new Set(scopedProjects.map(p=>p.id));
  const data={projects:scopedProjects,meetings:(meetings.data||[]).filter(m=>scopedIds.has(m.project_id)),actions:(actions.data||[]).filter(a=>scopedIds.has(a.project_id)),decisions:(decisions.data||[]).filter(d=>scopedIds.has(d.project_id))};
  const loading=[projects,meetings,actions,decisions].some(query=>query.isLoading);
  const loadError=[projects,meetings,actions,decisions].find(query=>query.isError)?.error;
  function notify(message:string){setToast(message);window.setTimeout(()=>setToast(""),2600);}
  const remove=useMutation({mutationFn:({type,id}:{type:EntityType;id:number})=>api(`${endpoints[type]}/${id}`,{method:"DELETE"}),onSuccess:async()=>{await queryClient.invalidateQueries();notify("삭제했습니다.");}});
  useEffect(()=>{const params=new URLSearchParams(window.location.search);const oauthToken=params.get("token");const token=oauthToken||localStorage.getItem("decisionflow_token");if(oauthToken){localStorage.setItem("decisionflow_token",oauthToken);setAuthenticated(true);if(params.get("onboarding")==="1"){setOnboarding(true);setView("settings");}window.history.replaceState({},document.title,window.location.pathname);}if(!token){setAuthChecking(false);return;}api<AuthUser>("/auth/me").then(current=>{setUser(current);if(oauthToken)notify(`${current.nickname||current.email}님, 환영합니다.`);}).catch(()=>{localStorage.removeItem("decisionflow_token");setAuthenticated(false);}).finally(()=>setAuthChecking(false));},[]);
  function handleAuth(current:AuthUser,isNew:boolean){setUser(current);setAuthenticated(true);setAuthChecking(false);if(isNew){setOnboarding(true);setView("settings");}notify(`${current.nickname||current.email}님, 환영합니다.`);}
  async function logout(){try{await api("/auth/logout",{method:"POST"});}finally{localStorage.removeItem("decisionflow_token");setUser(null);setAuthenticated(false);setOnboarding(false);setWorkspaceId(null);setModal(null);setReview(null);setSpeakerReview(null);setProjectTarget(null);setSidebarOpen(false);setView("dashboard");queryClient.clear();}}
  if(authChecking) return <div className="auth-loading">로그인 상태를 확인하는 중...</div>;
  if(!authenticated||!user) return <><AuthPage onAuth={handleAuth} onNotify={notify}/>{toast&&<div className="toast">{toast}</div>}</>;
  async function refresh(){await queryClient.invalidateQueries();notify("새로고침했습니다.");}

  async function onDelete(type:EntityType,id:number){if(window.confirm("이 항목을 삭제할까요?"))remove.mutate({type,id});}
  async function onEdit(type:EntityType,id:number){let item=(data[type] as Entity[]).find(value=>value.id===id)||null;if(type==="meetings")item=await api<Meeting>(`/meetings/${id}`);setModal({type,item});}
  async function onSave(payload:Record<string,unknown>){if(!modal)return;if(modal.type==="projects"&&!modal.item&&workspaceId)payload.workspace_id=workspaceId;const id=modal.item?.id;await api(`${endpoints[modal.type]}${id?`/${id}`:""}`,{method:id?"PATCH":"POST",body:JSON.stringify(payload)});setModal(null);await queryClient.invalidateQueries();notify(id?"수정했습니다.":"저장했습니다.");}
  async function onNotion(id:number){try{const result=await api<{status:string}>(`/meetings/${id}/notion-sync`,{method:"POST"});await queryClient.invalidateQueries({queryKey:["meetings",user?.id]});notify(result.status==="ALREADY_SYNCED"?"이미 Notion에 동기화됐습니다.":"Notion에 전송했습니다.");}catch(error){notify(error instanceof Error?error.message:"Notion 전송에 실패했습니다.");}}
  async function onReview(id:number){setReviewingId(id);try{const meeting=await api<Meeting>(`/meetings/${id}`);const result=await api<{meeting_id:number;candidates:DecisionCandidate[]}>(`/meetings/${id}/decision-candidates`,{method:"POST"});setReview({meeting,candidates:result.candidates});}catch(error){notify(error instanceof Error?error.message:"결정사항 분석에 실패했습니다.");}finally{setReviewingId(null);}}
  async function onSummarize(id:number){setSummarizingId(id);try{await api<Meeting>(`/meetings/${id}/summarize`,{method:"POST"});await queryClient.invalidateQueries({queryKey:["meetings",user?.id]});await queryClient.invalidateQueries({queryKey:["project-meeting-details"]});notify("쟁점 중심 요약을 저장했습니다.");}catch(error){notify(error instanceof Error?error.message:"회의 요약에 실패했습니다.");}finally{setSummarizingId(null);}}
  async function onConfirm(items:DecisionCandidate[]){if(!review)return;setSavingReview(true);try{await api(`/meetings/${review.meeting.id}/decisions/confirm`,{method:"POST",body:JSON.stringify({decisions:items.map(({topic,value})=>({topic,value}))})});await queryClient.invalidateQueries({queryKey:["decisions"]});setReview(null);notify(`${items.length}개 결정사항을 확정했습니다.`);}catch(error){notify(error instanceof Error?error.message:"결정사항 저장에 실패했습니다.");}finally{setSavingReview(false);}}
  async function onSpeakerAnalysis(id:number){setAnalyzingSpeakersId(id);try{const meeting=await api<Meeting>(`/meetings/${id}`);const analysis=await api<SpeakerAnalysis>(`/meetings/${id}/speaker-analysis`,{method:"POST",body:JSON.stringify({speaker_names:meeting.speaker_names||{}})});setSpeakerReview({meeting,analysis});}catch(error){notify(error instanceof Error?error.message:"화자별 분석에 실패했습니다.");}finally{setAnalyzingSpeakersId(null);}}
  async function onConfirmActions(items:ActionItemCandidate[]){if(!speakerReview)return;setSavingActions(true);try{await api(`/meetings/${speakerReview.meeting.id}/action-items/confirm`,{method:"POST",body:JSON.stringify({action_items:items.map(({task,assignee,due_date,priority})=>({task,assignee,due_date,priority}))})});await queryClient.invalidateQueries({queryKey:["actions",user?.id]});setSpeakerReview(null);notify(`${items.length}개 Action Item을 저장했습니다.`);}catch(error){notify(error instanceof Error?error.message:"Action Item 저장에 실패했습니다.");}finally{setSavingActions(false);}}
  async function onSaveSpeakerNames(speakerNames:Record<string,string>){if(!speakerReview)return;const meeting=await api<Meeting>(`/meetings/${speakerReview.meeting.id}`,{method:"PATCH",body:JSON.stringify({speaker_names:speakerNames})});setSpeakerReview(current=>current?{...current,meeting}:current);await queryClient.invalidateQueries({queryKey:["meetings",user?.id]});notify("화자 이름을 저장했습니다.");}
  function openProject(id:number){setProjectTarget({projectId:id});setView("projects");}
  function openMeeting(id:number){const meeting=data.meetings.find(item=>item.id===id);if(meeting){setProjectTarget({projectId:meeting.project_id,meetingId:id});setView("projects");}}
  function openAction(id:number){const action=data.actions.find(item=>item.id===id);if(action){setProjectTarget({projectId:action.project_id,meetingId:action.meeting_id||undefined,actionId:id});setView("projects");}}
  function openDecision(id:number){const decision=data.decisions.find(item=>item.id===id);if(decision){setProjectTarget({projectId:decision.project_id,meetingId:decision.meeting_id||undefined,decisionId:id});setView("projects");}}
  function createAction(projectId:number,meetingId?:number){setModal({type:"actions",item:null,defaults:{project_id:projectId,...(meetingId?{meeting_id:meetingId}:{})}});}
  const common={...data,userName:user.nickname||user.email.split("@")[0],onNavigate:(next:View)=>{setView(next);setProjectTarget(null);},onNewMeeting:()=>create("meetings"),onEdit,onDelete,onNotion,onReview,reviewingId,onSummarize,summarizingId,onSpeakerAnalysis,analyzingSpeakersId,onOpenProject:openProject,onOpenMeeting:openMeeting,onOpenAction:openAction,onOpenDecision:openDecision,onCreateAction:createAction};
  const Current={dashboard:HomeDashboard,projects:ProjectsPage,meetings:MeetingsPage,actions:ActionsPage,decisions:DecisionsPage}[view as Exclude<View,"settings"|"workflow">];
  function create(type?:EntityType){if(workspace?.role==="MEMBER"){notify("팀장에게 회의 또는 업무 생성을 요청해 주세요.");return;}const target=type||(view==="dashboard"?"projects":view as EntityType);if(target!=="projects"&&!data.projects.length){notify("프로젝트를 먼저 만들어 주세요.");setView("projects");return;}setModal({type:target,item:null});}
  const selectedProject=data.projects.find(project=>project.id===projectTarget?.projectId);
  return <div className="app-shell">
    <Sidebar view={view} open={sidebarOpen} onCreateMeeting={()=>create("meetings")} onToggle={()=>setSidebarOpen(value=>!value)} onChange={next=>{setView(next);setProjectTarget(null);setSidebarOpen(false);}}/>
    <main className="main-content">
      <header className="topbar"><div><span className="kicker">WORKSPACE</span><h1>{pageNames[view]}</h1></div><div className="topbar-right"><select aria-label="Workspace 전환" value={workspaceId??0} onChange={e=>selectWorkspace(Number(e.target.value))}><option value="0">개인 프로젝트</option>{workspaces.data?.map(w=><option key={w.id} value={w.id}>{w.name} · {w.role}</option>)}</select>{view!=="settings"&&view!=="workflow"&&workspace?.role!=="MEMBER"&&<div className="top-actions"><button className="icon-control desktop-only" onClick={refresh} title="새로고침"><RefreshCw/></button><button className="button primary" onClick={()=>create(view==="dashboard"?"meetings":undefined)}><Plus/>{createNames[view==="dashboard"?"meetings":view as EntityType]}</button></div>}<div className="user-session"><UserRound/><span><b>{user.nickname||user.email.split("@")[0]}님</b><small>로그인 중</small></span><button className="icon-control" onClick={logout} title="로그아웃"><LogOut/></button></div></div></header>
      <Suspense fallback={<div className="loading">협업 화면을 불러오는 중...</div>}>{view==="settings"?<SettingsPage onNotify={notify} onboarding={onboarding} onOnboardingComplete={()=>setOnboarding(false)}/>:view==="workflow"||(view==="dashboard"&&workspace)?<WorkflowPage key={workspace?.id||"none"} workspace={workspace} user={user} projects={data.projects} meetings={data.meetings} onNotify={notify} onSelectWorkspace={selectWorkspace}/>:loading?<div className="loading">데이터를 불러오는 중...</div>:loadError?<div className="page"><section className="panel" role="alert"><h2>데이터를 불러오지 못했습니다.</h2><p>{loadError instanceof Error?loadError.message:"잠시 후 다시 시도해 주세요."}</p><button className="button soft" onClick={refresh}>다시 시도</button></section></div>:selectedProject?<ProjectDetailPage {...common} project={selectedProject} target={projectTarget||undefined} onBack={()=>setProjectTarget(null)}/>:<Current {...common}/>}</Suspense>
    </main>
    {modal&&<EntityModal {...modal} projects={data.projects} onClose={()=>setModal(null)} onSave={onSave}/>} 
    {review&&<DecisionReviewModal meeting={review.meeting} candidates={review.candidates} saving={savingReview} onClose={()=>setReview(null)} onConfirm={onConfirm}/>} 
    {speakerReview&&<SpeakerAnalysisModal meeting={speakerReview.meeting} analysis={speakerReview.analysis} saving={savingActions} onClose={()=>setSpeakerReview(null)} onConfirm={onConfirmActions} onSaveSpeakerNames={onSaveSpeakerNames}/>}
    {toast&&<div className="toast">{toast}</div>}
  </div>;
}
