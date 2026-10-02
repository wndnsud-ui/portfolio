import { CheckCircle2, Info, KeyRound, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "./api";

interface Status { openai_configured:boolean; notion_api_configured:boolean; notion_database_configured:boolean; }
const initial:Status={openai_configured:false,notion_api_configured:false,notion_database_configured:false};

export default function SettingsPage({onNotify,onboarding=false,onOnboardingComplete}:{onNotify:(message:string)=>void;onboarding?:boolean;onOnboardingComplete?:()=>void}) {
  const [status,setStatus]=useState<Status>(initial);
  const [values,setValues]=useState({openai_api_key:"",notion_api_key:"",notion_database_id:""});
  const [saving,setSaving]=useState(false);
  useEffect(()=>{api<Status>("/settings").then(setStatus).catch(error=>onNotify(error instanceof Error?error.message:"설정을 불러오지 못했습니다."));},[]);
  const field=(name:keyof typeof values)=>({value:values[name],onChange:(event:React.ChangeEvent<HTMLInputElement>)=>setValues(current=>({...current,[name]:event.target.value}))});
  async function save(event:React.FormEvent){event.preventDefault();const payload=Object.fromEntries(Object.entries(values).filter(([,value])=>value.trim()));if(!Object.keys(payload).length){onNotify("변경할 키를 입력해 주세요.");return;}setSaving(true);try{setStatus(await api<Status>("/settings",{method:"PUT",body:JSON.stringify(payload)}));setValues({openai_api_key:"",notion_api_key:"",notion_database_id:""});onOnboardingComplete?.();onNotify("연동 설정을 저장했습니다.");}catch(error){onNotify(error instanceof Error?error.message:"설정을 저장하지 못했습니다.");}finally{setSaving(false);}}
  return <div className="page settings-page">{onboarding&&<div className="onboarding-notice"><Info/><div><strong>환영합니다. 시작하기 전에 API를 설정해 주세요.</strong><p>회의 전사와 AI 분석에는 OpenAI API Key가 필요합니다. Notion 연동은 선택 사항입니다.</p></div></div>}<header className="settings-heading"><span className="kicker">INTEGRATIONS</span><h2>외부 서비스 설정</h2><p>API 키는 사용자 계정별로 암호화해 저장하며 화면과 API 응답에 원문으로 노출하지 않습니다.</p></header><form className="settings-form" onSubmit={save} autoComplete="off"><section><div className="integration-title"><span className="integration-icon"><KeyRound/></span><div><h3>OpenAI</h3><p>음성 전사와 회의록 결정사항 분석에 사용합니다.</p></div><Status configured={status.openai_configured}/></div><label>OpenAI API Key<input type="password" placeholder={status.openai_configured?"••••••••••••••••  설정됨":"sk-..."} autoComplete="new-password" {...field("openai_api_key")}/></label></section><section><div className="integration-title"><span className="integration-icon notion-mark">N</span><div><h3>Notion</h3><p>회의록과 결정사항을 지정한 데이터베이스로 전송합니다.</p></div><Status configured={status.notion_api_configured&&status.notion_database_configured}/></div><label>Notion API Key<input type="password" placeholder={status.notion_api_configured?"••••••••••••••••  설정됨":"ntn_..."} autoComplete="new-password" {...field("notion_api_key")}/></label><label>Notion Database ID<input type="password" placeholder={status.notion_database_configured?"••••••••••••••••  설정됨":"Database ID"} autoComplete="new-password" {...field("notion_database_id")}/></label></section><footer><span>비워 둔 항목은 기존 값을 유지합니다.</span><button className="button primary" disabled={saving}><Save/>{saving?"저장 중...":"설정 저장"}</button></footer></form></div>;
}

function Status({configured}:{configured:boolean}) { return <span className={`config-status ${configured?"ready":""}`}>{configured&&<CheckCircle2/>}{configured?"설정됨":"미설정"}</span>; }
