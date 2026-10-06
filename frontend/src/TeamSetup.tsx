import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type { Workspace } from "./types";

type Invite = { id: number; workspace_name: string; role: string };
type Member = { user_id: number; nickname: string | null; email: string; role: string };
export const roleLabel = (role: string) => ({ OWNER: "팀장 · 소유자", MANAGER: "팀장", MEMBER: "팀원" }[role] || role);

export default function TeamSetup({ workspace, onSelect, onClose }: { workspace: Workspace | null; onSelect: (id: number) => void; onClose: () => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("MEMBER");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const invites = useQuery({ queryKey: ["received-invites"], queryFn: () => api<Invite[]>("/workspace-invites"), refetchInterval: 10000 });
  const members = useQuery({ queryKey: ["workspace-members", "team-setup", workspace?.id], enabled: !!workspace, queryFn: () => api<Member[]>(`/workspaces/${workspace!.id}/members`) });
  async function run(work: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try { await work(); await qc.invalidateQueries(); }
    catch (e) { setError(e instanceof Error ? e.message : "요청에 실패했습니다."); }
    finally { setBusy(false); }
  }
  return <div className="modal-backdrop"><section className="modal workflow-modal" role="dialog" aria-modal="true" aria-label="팀 만들기·초대">
    <header><h2>팀 만들기·초대</h2><button className="button ghost" onClick={onClose}>닫기</button></header>
    <div className="modal-body">
      <p>팀을 만들면 팀장으로 시작합니다. 초대받은 사람은 지정된 역할로 참여하며, 역할은 팀마다 달라질 수 있습니다.</p>
      <form onSubmit={e => { e.preventDefault(); void run(async () => { const w = await api<Workspace>("/workspaces", { method: "POST", body: JSON.stringify({ name: name.trim() }) }); await qc.invalidateQueries({ queryKey: ["workspaces"] }); onSelect(w.id); setName(""); setMessage("팀을 만들었습니다. 아래에서 팀원을 초대하세요."); }); }}>
        <h3>새 팀 만들기</h3><label>팀 이름<input required maxLength={200} value={name} onChange={e => setName(e.target.value)} placeholder="예: 서비스 개발팀" /></label>
        <button className="button primary" disabled={busy || !name.trim()}>팀장으로 팀 만들기</button>
      </form>
      <section><h3>받은 초대</h3><p>초대받은 이메일로 가입·로그인하면 여기에 표시됩니다.</p>
        {invites.isError && <p role="alert">{invites.error.message}</p>}
        {invites.data?.map(i => <article className="workflow-entry" key={i.id}><b>{i.workspace_name}</b><p>{roleLabel(i.role)}로 초대받았습니다.</p><button className="button primary" disabled={busy} onClick={() => void run(async () => { const r = await api<{ workspace_id: number }>(`/workspace-invites/${i.id}/accept`, { method: "POST" }); await qc.invalidateQueries({ queryKey: ["workspaces"] }); onSelect(r.workspace_id); setMessage("초대를 수락했습니다."); })}>초대 수락</button></article>)}
        {!invites.isLoading && !invites.isError && !invites.data?.length && <p>받은 초대가 없습니다.</p>}
      </section>
      {workspace && <section><h3>{workspace.name} · {roleLabel(workspace.role)}</h3>
        {workspace.role === "OWNER" ? <form onSubmit={e => { e.preventDefault(); void run(async () => { await api(`/workspaces/${workspace.id}/invites`, { method: "POST", body: JSON.stringify({ email: email.trim(), role }) }); setEmail(""); setMessage("초대를 등록했습니다. 상대방이 해당 이메일로 로그인해 ‘팀 만들기·초대’에서 수락할 수 있습니다."); }); }}>
          <label>초대할 이메일<input type="email" required value={email} onChange={e => setEmail(e.target.value)} /></label>
          <label>참여 역할<select value={role} onChange={e => setRole(e.target.value)}><option value="MEMBER">팀원</option><option value="MANAGER">팀장</option></select></label>
          <p>초대는 7일간 유효합니다. 이메일 발송 없이 앱에서 수락합니다.</p><button className="button primary" disabled={busy}>팀원 초대</button>
        </form> : <p>팀 초대와 역할 변경은 팀 소유자가 관리합니다.</p>}
        {members.isError && <p role="alert">{members.error.message}</p>}
        {members.data?.map(m => <article className="workflow-entry" key={m.user_id}><b>{m.nickname || m.email}</b><p>{m.email} · {roleLabel(m.role)}</p>{workspace.role === "OWNER" && m.role !== "OWNER" && <button disabled={busy} className="button soft" onClick={() => void run(async () => { await api(`/workspaces/${workspace.id}/members/${m.user_id}`, { method: "PUT", body: JSON.stringify({ user_id: m.user_id, role: m.role === "MEMBER" ? "MANAGER" : "MEMBER" }) }); })}>{m.role === "MEMBER" ? "팀장으로 변경" : "팀원으로 변경"}</button>}</article>)}
        <p>참여한 팀원은 ‘검토 · 결재 · 알림 → 팀원’에서 프로젝트에 추가하면 업무를 배정할 수 있습니다.</p>
      </section>}
      {message && <p role="status">{message}</p>}{error && <p role="alert">{error}</p>}
    </div>
  </section></div>;
}
