import { LogIn, UserPlus, Sparkles, CheckSquare2, Users, FileText, Mail, LockKeyhole } from "lucide-react";
import { useEffect, useState } from "react";
import { api, apiBaseUrl } from "./api";
import type { AuthUser } from "./types";
import PasswordRecovery from "./PasswordRecovery";

interface AuthResponse {
  access_token: string;
  user: AuthUser;
}

export default function AuthPage({ onAuth, onNotify }: { onAuth: (user:AuthUser, isNew:boolean) => void; onNotify: (message: string) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ email: "", password: "", nickname: "", openai_api_key: "", notion_api_key: "", notion_database_id: "" });
  const [saving, setSaving] = useState(false);
  const [recovering,setRecovering]=useState(false);
  const [oauthError]=useState(()=>sessionStorage.getItem("decisionflow_oauth_error"));
  const [googleConfigured, setGoogleConfigured] = useState<boolean|null>(null);
  useEffect(()=>{api<{configured:boolean}>("/auth/google/status").then(result=>setGoogleConfigured(result.configured)).catch(()=>setGoogleConfigured(false));},[]);
  const field = (name: keyof typeof form) => ({
    value: form[name],
    onChange: (event: React.ChangeEvent<HTMLInputElement>) => setForm((current) => ({ ...current, [name]: event.target.value }))
  });
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const payload = mode === "login" ? { email: form.email, password: form.password } : Object.fromEntries(Object.entries(form).filter(([, value]) => value.trim()));
      const result = await api<AuthResponse>(mode === "login" ? "/auth/login" : "/auth/register", { method: "POST", body: JSON.stringify(payload) });
      localStorage.setItem("decisionflow_token", result.access_token);
      onAuth(result.user, mode === "register");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "인증에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }
  if(recovering)return <PasswordRecovery onBack={()=>setRecovering(false)}/>;
  return <main className="auth-shell"><div className="auth-layout"><section className="auth-story"><div className="brand"><span>D</span><b>Decision<span className="brand-accent">Flow</span></b></div><h1>회의에서 나온 결정이<br/>팀의 실행으로 이어집니다.</h1><p>흩어진 회의 기록을 하나로 모으고,<br/>팀의 다음 할 일을 명확하게 정리하세요.</p><ul>{[[Sparkles,"AI 회의록 자동 정리"],[CheckSquare2,"업무 배분 및 진행 관리"],[Users,"팀 협업 및 결재"],[FileText,"Notion 연동 · 회의 기록 동기화"]].map(([Icon,title])=>{const FeatureIcon=Icon as typeof Sparkles;return <li key={String(title)}><span><FeatureIcon/></span>{String(title)}</li>;})}</ul><small>회의의 시작부터, 실행의 마지막까지.</small></section><section className="auth-panel">{oauthError&&<p role="alert" className="onboarding-notice">{({google_network:"서버가 Google 인증 서버에 연결하지 못했습니다.",google_credentials:"Google 클라이언트 ID 또는 Secret을 확인해 주세요.",google_code_expired:"인증 코드가 만료되었습니다. Google 로그인을 새로 시작해 주세요.",google_cancelled:"Google 로그인이 취소되었습니다."} as Record<string,string>)[oauthError]||"Google 인증 처리에 실패했습니다."}</p>}<div className="auth-tabs" role="tablist" aria-label="계정 접속">{(["login","register"] as const).map(tab=><button role="tab" aria-selected={mode===tab} className={mode===tab?"active":""} key={tab} onClick={()=>setMode(tab)}>{tab==="login"?"로그인":"회원가입"}</button>)}</div><h2>{mode==="login"?"다시 만나 반가워요":"팀의 새로운 흐름을 시작하세요"}</h2><p className="auth-intro">{mode==="login"?"오늘의 결정과 업무를 확인하세요.":"계정을 만들고 협업 공간에 참여하세요."}</p>{googleConfigured?<a className="google-button" onClick={()=>sessionStorage.removeItem("decisionflow_oauth_error")} href={`${apiBaseUrl}/auth/google/login`}><span className="google-mark">G</span>{mode==="login"?"Google로 계속하기":"Google로 회원가입"}</a>:<button className="google-button" disabled><span className="google-mark">G</span>{googleConfigured===null?"Google 로그인 확인 중":"Google 로그인 설정 필요"}</button>}<div className="divider"><span>이메일로 {mode==="login"?"로그인":"회원가입"}</span></div><form onSubmit={submit}>{mode === "register" && <label>닉네임<input placeholder="팀에서 사용할 이름" autoComplete="nickname" {...field("nickname")} /></label>}<label>이메일<div className="auth-input"><Mail/><input type="email" placeholder="example@company.com" autoComplete="email" required {...field("email")} /></div></label><label>비밀번호<div className="auth-input"><LockKeyhole/><input type="password" placeholder="8자 이상 입력하세요" autoComplete={mode==="login"?"current-password":"new-password"} required minLength={8} {...field("password")} /></div></label>{mode === "register" && <details className="auth-settings"><summary>서비스 연동 설정 (선택)</summary><label>OpenAI API Key<input type="password" {...field("openai_api_key")} /></label><label>Notion API Key<input type="password" {...field("notion_api_key")} /></label><label>Notion Database ID<input type="password" {...field("notion_database_id")} /></label></details>}<button className="button primary" disabled={saving}>{mode === "login" ? <LogIn /> : <UserPlus />}{saving ? "처리 중..." : mode === "login" ? "로그인" : "회원가입"}</button></form>{mode==="login"&&<p className="auth-switch"><button type="button" onClick={()=>setRecovering(true)}>비밀번호를 잊으셨나요?</button></p>}<p className="auth-switch">{mode==="login"?"아직 계정이 없으신가요?":"이미 계정이 있으신가요?"}<button onClick={()=>setMode(mode==="login"?"register":"login")}>{mode==="login"?"회원가입":"로그인"}</button></p></section></div></main>;
}
