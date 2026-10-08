import { useEffect, useState } from "react";
import { api } from "./api";

export default function PasswordRecovery({token,onBack}:{token?:string;onBack:()=>void}) {
  const [email,setEmail]=useState("");
  const [password,setPassword]=useState("");
  const [confirmation,setConfirmation]=useState("");
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState("");
  const [error,setError]=useState("");
  const [done,setDone]=useState(false);
  useEffect(()=>{if(token)window.history.replaceState({},document.title,window.location.pathname);},[token]);
  async function submit(e:React.FormEvent) {
    e.preventDefault();setError("");setMessage("");
    if(token&&password!==confirmation){setError("비밀번호가 일치하지 않습니다.");return;}
    setBusy(true);
    try {
      const result=await api<{message:string}>(token?"/auth/reset-password":"/auth/forgot-password",{method:"POST",body:JSON.stringify(token?{token,password}:{email})});
      setMessage(result.message);
      if(token){localStorage.removeItem("decisionflow_token");setDone(true);setPassword("");setConfirmation("");}
    } catch(e){setError(e instanceof Error?e.message:"요청을 처리하지 못했습니다.");}
    finally{setBusy(false);}
  }
  return <main className="auth-shell"><section className="auth-panel" style={{maxWidth:440,borderRadius:20}}>
    <h2>{token?"새 비밀번호 설정":"비밀번호 찾기"}</h2>
    <p className="auth-intro">{token?"새 비밀번호는 8자 이상으로 설정해 주세요.":"가입한 이메일로 30분 동안 유효한 재설정 링크를 보내드립니다."}</p>
    {!done&&<form onSubmit={submit}>{token?<><label>새 비밀번호<input type="password" autoComplete="new-password" required minLength={8} maxLength={128} value={password} onChange={e=>setPassword(e.target.value)}/></label><label>새 비밀번호 확인<input type="password" autoComplete="new-password" required value={confirmation} onChange={e=>setConfirmation(e.target.value)}/></label></>:<label>이메일<input type="email" autoComplete="email" required value={email} onChange={e=>setEmail(e.target.value)}/></label>}<button className="button primary" disabled={busy}>{busy?"처리 중...":token?"비밀번호 변경":"재설정 링크 보내기"}</button></form>}
    {message&&<p role="status">{message}</p>}{error&&<p role="alert">{error}</p>}
    <p className="auth-switch"><button onClick={onBack}>로그인으로 돌아가기</button></p>
  </section></main>;
}
