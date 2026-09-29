export type View = "dashboard" | "projects" | "meetings" | "actions" | "decisions" | "settings";
export type EntityType = "projects" | "meetings" | "actions" | "decisions";

export interface Project { id:number; name:string; description:string | null; created_at:string; updated_at:string; }
export interface Meeting { id:number; project_id:number; title:string; meeting_date:string; participants:string[]; summary:string | null; discussion:string | null; undecided_topics:string[]; analysis_status:string; notion_sync_status:string; transcript?:string | null; created_at:string; updated_at:string; }
export interface ActionItem { id:number; project_id:number; meeting_id:number | null; task:string; assignee:string | null; due_date:string | null; status:string; priority:string; risk_score:number; risk_level:string; created_at:string; updated_at:string; completed_at:string | null; }
export interface Decision { id:number; project_id:number; meeting_id:number | null; topic:string; value:string; status:string; created_at:string; updated_at:string; }
export interface DecisionCandidate { topic:string; value:string; evidence:string; confidence:number; }
export type Entity = Project | Meeting | ActionItem | Decision;
