export type View = "dashboard" | "projects" | "meetings" | "actions" | "decisions" | "settings" | "workflow" | "team";
export type EntityType = "projects" | "meetings" | "actions" | "decisions";

export interface Workspace { id:number; name:string; role:"OWNER"|"MANAGER"|"MEMBER"; }
export interface Project { is_example?:boolean; id:number; workspace_id?:number|null; name:string; description:string | null; created_at:string; updated_at:string; }
export interface Meeting { id:number; recorder_id?:number|null; report_status?:string; input_type?:string; candidates?:Record<string,unknown>; project_id:number; title:string; meeting_date:string; participants:string[]; speaker_names:Record<string,string>; summary:string | null; discussion:string | null; undecided_topics:string[]; analysis_status:string; notion_sync_status:string; transcript?:string | null; created_at:string; updated_at:string; }
export interface ActionItem { progress_percent?:number|null; progress_updated_at?:string|null; progress_content?:string|null; id:number; assignee_id?:number|null; description?:string|null; workflow_status?:string|null; project_id:number; meeting_id:number | null; task:string; assignee:string | null; due_date:string | null; status:string; priority:string; risk_score:number; risk_level:string; created_at:string; updated_at:string; completed_at:string | null; }
export interface Decision { id:number; project_id:number; meeting_id:number | null; topic:string; value:string; status:string; created_at:string; updated_at:string; }
export interface DecisionCandidate { topic:string; value:string; evidence:string; confidence:number; }
export type Entity = Project | Meeting | ActionItem | Decision;
export interface AuthUser { id:number; email:string; nickname:string | null; created_at:string; }
export interface SpeakerIssue { speaker:string; points:string[]; stance:string; }
export interface ActionItemCandidate { task:string; assignee:string|null; due_date:string|null; priority:string; evidence:string; confidence:number; }
export interface SpeakerAnalysis { meeting_id:number; summary:string; issues:string[]; speakers:SpeakerIssue[]; action_items:ActionItemCandidate[]; }
