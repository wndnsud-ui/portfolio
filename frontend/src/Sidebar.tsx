import { CheckSquare2, FolderKanban, Gauge, Menu, Scale, Settings, Video } from "lucide-react";
import type { View } from "./types";

const items: {id:View; label:string; icon:typeof Gauge}[] = [
  { id:"dashboard", label:"대시보드", icon:Gauge }, { id:"projects", label:"프로젝트", icon:FolderKanban },
  { id:"meetings", label:"회의", icon:Video }, { id:"actions", label:"업무", icon:CheckSquare2 }, { id:"decisions", label:"결정사항", icon:Scale },
  { id:"settings", label:"설정", icon:Settings }
];

export default function Sidebar({ view, onChange, open, onToggle }:{view:View; onChange:(view:View)=>void; open:boolean; onToggle:()=>void}) {
  return <aside className={`sidebar ${open ? "open" : ""}`}>
    <div className="brand"><span>DF</span><b>DecisionFlow</b><button className="mobile-menu" onClick={onToggle} title="메뉴"><Menu/></button></div>
    <nav>{items.map(item => <button key={item.id} className={view === item.id ? "active" : ""} onClick={() => onChange(item.id)}><item.icon/><span>{item.label}</span></button>)}</nav>
    <div className="workspace-status"><i/>Local workspace</div>
  </aside>;
}
