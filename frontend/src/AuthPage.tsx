import { LogIn, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { api, apiBaseUrl } from "./api";
import type { AuthUser } from "./types";

interface AuthResponse {
  access_token: string;
  user: AuthUser;
}

export default function AuthPage({ onAuth, onNotify }: { onAuth: (user:AuthUser, isNew:boolean) => void; onNotify: (message: string) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ email: "", password: "", nickname: "", openai_api_key: "", notion_api_key: "", notion_database_id: "" });
  const [saving, setSaving] = useState(false);
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
  return <main className="auth-shell"><section className="auth-panel"><h1>DecisionFlow</h1><div className="auth-tabs" role="tablist"><button className={mode==="login"?"active":""} onClick={()=>setMode("login")}>로그인</button><button className={mode==="register"?"active":""} onClick={()=>setMode("register")}>회원가입</button></div>{googleConfigured?<a className="google-button" href={`${apiBaseUrl}/auth/google/login`}>G {mode==="login"?"Google로 로그인":"Google로 회원가입"}</a>:<button className="google-button" disabled>G {googleConfigured===null?"Google 로그인 확인 중":"Google 로그인 설정 필요"}</button>}<div className="divider"><span>또는 이메일로</span></div><form onSubmit={submit}>{mode === "register" && <input placeholder="닉네임" {...field("nickname")} />}<input type="email" placeholder="이메일" required {...field("email")} /><input type="password" placeholder="비밀번호" required minLength={8} {...field("password")} />{mode === "register" && <div className="auth-settings"><input type="password" placeholder="OpenAI API Key (선택)" {...field("openai_api_key")} /><input type="password" placeholder="Notion API Key (선택)" {...field("notion_api_key")} /><input type="password" placeholder="Notion Database ID (선택)" {...field("notion_database_id")} /></div>}<button className="button primary" disabled={saving}>{mode === "login" ? <LogIn /> : <UserPlus />}{saving ? "처리 중..." : mode === "login" ? "로그인" : "회원가입"}</button></form></section></main>;
}
