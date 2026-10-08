import { useState } from "react";
import { ArrowLeft, ArrowRight, UserRound, Users, Mail, X } from "lucide-react";
import "./FirstUseTutorial.css";

type Track="personal"|"leader"|"member";
type Action="personal-project"|"personal-task"|"create-team"|"team"|"team-project"|"team-task"|"workflow";
const tracks={
  personal:{label:"혼자 사용하기",Icon:UserRound,steps:[
    {title:"개인 프로젝트 만들기",text:"개인 프로젝트는 나만 사용하는 공간입니다. 프로젝트 이름을 입력하고 저장하세요.",action:"personal-project",button:"프로젝트 만들기"},
    {title:"첫 업무 등록하기",text:"프로젝트를 선택하고 업무 제목과 기한을 입력하세요. 담당자를 나로 선택하면 업무 시작과 진행 기록을 사용할 수 있습니다.",action:"personal-task",button:"새 업무 등록"},
    {title:"업무 진행하기",text:"홈의 업무 카드를 열어 수락하고 시작하세요. 시작·중간·마무리 단계를 기록하고 결과를 제출한 뒤 완료를 승인하세요.",action:"workflow",button:"내 업무 확인"},
  ]},
  leader:{label:"팀장으로 시작하기",Icon:Users,steps:[
    {title:"팀 만들기",text:"팀 이름을 입력하면 팀장 권한으로 새 팀에 들어갑니다. 개인 공간도 계속 사용할 수 있습니다.",action:"create-team",button:"팀 만들기"},
    {title:"팀원 초대하기",text:"팀 관리에서 이메일로 가입된 팀원을 바로 추가하거나 초대 코드를 전달하세요. 초대받은 사람은 같은 이메일로 로그인해 수락합니다.",action:"team",button:"팀 관리 열기"},
    {title:"팀 프로젝트 만들기",text:"상단에서 팀을 선택하고 프로젝트를 만드세요. 팀 관리에서 팀원을 해당 프로젝트에도 추가해야 업무를 배정할 수 있습니다.",action:"team-project",button:"팀 프로젝트 만들기"},
    {title:"업무 배정하기",text:"팀 프로젝트의 새 업무에서 담당 팀원을 선택하세요. 팀원은 수락·시작·결과 제출을 진행하고, 팀장은 제출된 결과를 승인합니다.",action:"team-task",button:"업무 배정 화면"},
  ]},
  member:{label:"팀원으로 참여하기",Icon:Mail,steps:[
    {title:"초대 수락하기",text:"팀 관리 화면의 받은 초대 코드 칸에 코드를 넣고 초대 수락을 누르세요. 초대받은 이메일과 로그인 계정이 같아야 합니다.",action:"team",button:"초대 수락 화면"},
    {title:"팀과 프로젝트 확인하기",text:"상단에서 초대받은 팀을 선택하세요. 프로젝트가 보이지 않으면 팀장에게 프로젝트 참여 등록을 요청하세요.",action:"team",button:"참여 팀 확인"},
    {title:"배정된 업무 시작하기",text:"내 업무에서 업무를 열고 수락 → 시작을 누르세요. 진행 단계를 기록하고 결과를 제출하면 팀장이 검토합니다.",action:"workflow",button:"내 업무 열기"},
  ]},
} as const;

export default function FirstUseTutorial({onAction,onClose}:{onAction:(action:Action)=>void;onClose:()=>void}) {
  const [track,setTrack]=useState<Track|null>(null);const [step,setStep]=useState(0);
  const selected=track?tracks[track]:null;const current=selected?.steps[step];
  return <aside className="first-use-tutorial" aria-label="시작 튜토리얼">
    <header><span>시작 튜토리얼</span><button type="button" aria-label="튜토리얼 닫기" onClick={onClose}><X size={18}/></button></header>
    {!selected?<><h2>어떻게 시작할까요?</h2><p>원하는 흐름을 선택하세요. 안내 중에도 실제 화면을 사용할 수 있습니다.</p><div className="tutorial-tracks">{(Object.keys(tracks) as Track[]).map(key=>{const item=tracks[key];return <button key={key} onClick={()=>{setTrack(key);setStep(0);}}><item.Icon size={20}/>{item.label}<ArrowRight size={16}/></button>;})}</div></>:current&&<><div className="tutorial-step-count">{selected.label} · {step+1}/{selected.steps.length}</div><h2>{current.title}</h2><p>{current.text}</p><button className="button primary" onClick={()=>onAction(current.action)}>{current.button}<ArrowRight size={16}/></button><div className="tutorial-navigation"><button className="button ghost" onClick={()=>step?setStep(step-1):setTrack(null)}><ArrowLeft size={14}/>{step?"이전":"다른 흐름"}</button><button className="button soft" onClick={()=>step+1===selected.steps.length?onClose():setStep(step+1)}>{step+1===selected.steps.length?"안내 마치기":"다음 안내"}</button></div></>}
    <footer><button onClick={onClose}>건너뛰기</button><small>상단 튜토리얼 버튼에서 다시 볼 수 있어요.</small></footer>
  </aside>;
}
