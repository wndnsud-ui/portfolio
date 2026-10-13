import { Camera, ImagePlus, ScanText, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, apiBaseUrl } from "./api";
import type { Meeting } from "./types";
import "./PhotoCapture.css";

export type Attachment={id:number;file_name?:string;author?:string;user_id?:number;uploaded_by?:number;created_at:string};

export const ATTACHMENT_ACCEPT=".pdf,.docx,.xlsx,.png,.jpg,.jpeg,.webp,.heic,.heif,.txt,.md,image/*";
const MAX_EDGE=2560;
const isImageName=(name="")=>/\.(png|jpe?g|webp|heic|heif)$/i.test(name);
const browserCanShow=(name="")=>/\.(png|jpe?g|webp)$/i.test(name);
// Formats the vision model accepts; HEIC must be re-uploaded as JPEG first.
const canReadText=browserCanShow;
const imageType=(name="")=>/\.png$/i.test(name)?"image/png":/\.webp$/i.test(name)?"image/webp":"image/jpeg";

function stampName(){const d=new Date();const p=(n:number)=>String(n).padStart(2,"0");return `photo-${d.getFullYear()}${p(d.getMonth()+1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;}

/** Shrinks large phone photos (and converts HEIC where the browser can decode it) to JPEG before upload. */
export async function prepareImage(file:File):Promise<File>{
  const heic=/\.(heic|heif)$/i.test(file.name)||/hei[cf]/i.test(file.type);
  if(!file.type.startsWith("image/")&&!heic)return file;
  try{
    const bitmap=await createImageBitmap(file,{imageOrientation:"from-image"} as ImageBitmapOptions);
    const scale=Math.min(1,MAX_EDGE/Math.max(bitmap.width,bitmap.height));
    if(scale===1&&!heic&&file.size<1.5*1024*1024){bitmap.close();return file;}
    const canvas=document.createElement("canvas");canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);
    canvas.getContext("2d")!.drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();
    const blob=await new Promise<Blob|null>(resolve=>canvas.toBlob(resolve,"image/jpeg",0.85));
    if(!blob)return file;
    // Camera captures are often named "image.jpg"; give them a sortable, readable name.
    const base=/^image\.\w+$/i.test(file.name)||!file.name?stampName():file.name.replace(/\.[^.]+$/,"");
    return new File([blob],`${base}.jpg`,{type:"image/jpeg"});
  }catch{return file;}
}

export async function uploadFiles(path:string,files:File[],onProgress?:(done:number,total:number)=>void){
  for(let i=0;i<files.length;i++){onProgress?.(i,files.length);const body=new FormData();body.append("file",await prepareImage(files[i]));await api(path,{method:"POST",body});}
  onProgress?.(files.length,files.length);
}

/** Camera button opens the rear camera directly on phones; the other picks existing photos or documents. */
export function CaptureButtons({onFiles,disabled,status}:{onFiles:(files:File[])=>void;disabled?:boolean;status?:string}){
  const pick=(e:React.ChangeEvent<HTMLInputElement>)=>{const files=[...(e.target.files||[])];e.target.value="";if(files.length)onFiles(files);};
  return <div className="capture-buttons">
    <label className={`button primary capture-button ${disabled?"disabled":""}`}><Camera/>사진 촬영<input type="file" accept="image/*" capture="environment" disabled={disabled} onChange={pick}/></label>
    <label className={`button soft capture-button ${disabled?"disabled":""}`}><ImagePlus/>사진 · 파일 선택<input type="file" multiple accept={ATTACHMENT_ACCEPT} disabled={disabled} onChange={pick}/></label>
    {status&&<span role="status">{status}</span>}
  </div>;
}

async function fetchBlob(url:string){const response=await fetch(url,{headers:{Authorization:`Bearer ${localStorage.getItem("decisionflow_token")}`}});if(!response.ok)throw new Error("파일을 불러오지 못했습니다.");return response.blob();}

export async function downloadAttachment(url:string,name:string){const href=URL.createObjectURL(await fetchBlob(url));const a=document.createElement("a");a.href=href;a.download=name;a.click();window.setTimeout(()=>URL.revokeObjectURL(href),1000);}

function Thumb({item,url,onOpen}:{item:Attachment;url:string;onOpen:(src:string)=>void}){
  const [src,setSrc]=useState("");const [failed,setFailed]=useState(false);
  useEffect(()=>{if(!browserCanShow(item.file_name))return;let href="";let alive=true;fetchBlob(url).then(blob=>{href=URL.createObjectURL(new Blob([blob],{type:imageType(item.file_name)}));if(alive)setSrc(href);else URL.revokeObjectURL(href);}).catch(()=>setFailed(true));return()=>{alive=false;if(href)URL.revokeObjectURL(href);};},[url,item.file_name]);
  if(!browserCanShow(item.file_name)||failed)return <span className="photo-thumb placeholder">{(item.file_name?.split(".").pop()||"파일").toUpperCase()}</span>;
  return src?<button type="button" className="photo-thumb" onClick={()=>onOpen(src)}><img src={src} alt={item.file_name||"첨부 사진"} loading="lazy"/></button>:<span className="photo-thumb placeholder">불러오는 중</span>;
}

/** Thumbnail grid with a full-screen viewer for image attachments. */
export function PhotoGallery({items,fileUrl,canDelete,onDelete,onNotify,extraAction}:{items:Attachment[];fileUrl:(id:number)=>string;canDelete?:(item:Attachment)=>boolean;onDelete?:(item:Attachment)=>void;onNotify:(text:string)=>void;extraAction?:(item:Attachment)=>ReactNode}){
  const [open,setOpen]=useState<{src:string;item:Attachment}|null>(null);
  const photos=items.filter(item=>isImageName(item.file_name));
  if(!photos.length)return null;
  return <><div className="photo-grid">{photos.map(item=><figure key={item.id}><Thumb item={item} url={fileUrl(item.id)} onOpen={src=>setOpen({src,item})}/><figcaption><span title={item.file_name}>{item.file_name}</span><small>{item.author}</small><span className="photo-actions">{extraAction?.(item)}<button type="button" className="button ghost" onClick={()=>void downloadAttachment(fileUrl(item.id),item.file_name||"photo").catch(e=>onNotify(e.message))}>저장</button>{canDelete?.(item)&&onDelete&&<button type="button" className="icon-control" title="삭제" aria-label={`${item.file_name} 삭제`} onClick={()=>onDelete(item)}><Trash2/></button>}</span></figcaption></figure>)}</div>
  {open&&<div className="photo-viewer" role="dialog" aria-modal="true" aria-label={open.item.file_name} onClick={()=>setOpen(null)}><button type="button" className="icon-control" aria-label="닫기" onClick={()=>setOpen(null)}><X/></button><img src={open.src} alt={open.item.file_name||"첨부 사진"} onClick={e=>e.stopPropagation()}/></div>}</>;
}

/** Photos of whiteboards or paper minutes attached to a meeting, with AI text extraction into the transcript. */
export function MeetingPhotos({meetingId,userId,canManage,canEditTranscript=false,onNotify}:{meetingId:number;userId:number;canManage:boolean;canEditTranscript?:boolean;onNotify:(text:string)=>void}){
  const qc=useQueryClient();const [status,setStatus]=useState("");
  const [ocr,setOcr]=useState<{text:string;sources:string[]}|null>(null);const [reading,setReading]=useState("");const [saving,setSaving]=useState(false);
  const key=["meeting-attachments",userId,meetingId];
  const list=useQuery({queryKey:key,queryFn:()=>api<Attachment[]>(`/meetings/${meetingId}/attachments`)});
  const fileUrl=(id:number)=>`${apiBaseUrl}/meeting-attachments/${id}`;
  async function upload(files:File[]){try{await uploadFiles(`/meetings/${meetingId}/attachments`,files,(done,total)=>setStatus(done<total?`업로드 중 ${done+1}/${total}`:""));onNotify(`${files.length}개 파일을 올렸습니다.`);}catch(e){setStatus("");onNotify(e instanceof Error?e.message:"업로드에 실패했습니다.");}finally{await qc.invalidateQueries({queryKey:key});}}
  async function remove(item:Attachment){if(!window.confirm("이 파일을 삭제할까요?"))return;try{await api(`/meeting-attachments/${item.id}`,{method:"DELETE"});await qc.invalidateQueries({queryKey:key});}catch(e){onNotify(e instanceof Error?e.message:"삭제하지 못했습니다.");}}
  async function extract(items:Attachment[]){
    const parts:string[]=[];const sources:string[]=[];
    try{for(let i=0;i<items.length;i++){setReading(items.length>1?`글자 읽는 중 ${i+1}/${items.length}`:"글자 읽는 중...");const r=await api<{text:string}>(`/meeting-attachments/${items[i].id}/extract-text`,{method:"POST"});if(r.text){parts.push(items.length>1?`### ${items[i].file_name}\n\n${r.text}`:r.text);sources.push(items[i].file_name||"사진");}}
      if(!parts.length)onNotify("사진에서 읽을 수 있는 글자를 찾지 못했습니다.");else setOcr({text:parts.join("\n\n"),sources});
    }catch(e){onNotify(e instanceof Error?e.message:"글자를 추출하지 못했습니다.");if(parts.length)setOcr({text:parts.join("\n\n"),sources});}finally{setReading("");}
  }
  async function insert(mode:"append"|"replace"){
    if(!ocr?.text.trim())return;setSaving(true);
    try{const extracted=ocr.text.trim();let text=extracted;
      if(mode==="append"){const current=((await api<Meeting>(`/meetings/${meetingId}`)).transcript||"").trim();const block=`## 사진에서 옮긴 내용 (${ocr.sources.join(", ")})\n\n${extracted}`;text=current?`${current}\n\n${block}`:block;}
      await api(`/meetings/${meetingId}/input/text`,{method:"POST",body:JSON.stringify({text})});
      setOcr(null);await qc.invalidateQueries();onNotify(mode==="append"?"회의 원문 끝에 추가했습니다.":"회의 원문을 사진 내용으로 바꿨습니다.");
    }catch(e){onNotify(e instanceof Error?e.message:"회의 원문에 넣지 못했습니다.");}finally{setSaving(false);}
  }
  const files=list.data||[];const documents=files.filter(item=>!isImageName(item.file_name));const readable=files.filter(item=>canReadText(item.file_name));
  return <section className="record-block meeting-photos"><h4>회의 사진 · 문서</h4><p className="photo-hint">화이트보드나 종이 회의록을 휴대폰으로 바로 찍어 올리세요. 사진은 자동으로 용량을 줄여 올립니다.{canEditTranscript&&" 글자 추출을 누르면 AI가 사진 속 글자를 읽어 회의 원문에 넣을 수 있게 해 줍니다."}</p>
    <CaptureButtons onFiles={files=>void upload(files)} disabled={!!status} status={status}/>
    {canEditTranscript&&readable.length>1&&<button type="button" className="button soft" disabled={!!reading||saving} onClick={()=>void extract(readable)}><ScanText/>사진 {readable.length}장 글자 모두 추출</button>}
    {reading&&<p role="status" className="photo-hint">{reading} · 사진 한 장에 10~30초 정도 걸립니다.</p>}
    {list.isError&&<p role="alert">{list.error.message}</p>}
    <PhotoGallery items={files} fileUrl={fileUrl} canDelete={item=>canManage||item.uploaded_by===userId} onDelete={item=>void remove(item)} onNotify={onNotify} extraAction={item=>canEditTranscript&&canReadText(item.file_name)?<button type="button" className="button soft" disabled={!!reading||saving} onClick={()=>void extract([item])}><ScanText/>글자 추출</button>:null}/>
    {ocr&&<div className="ocr-review" role="region" aria-label="추출한 글자 확인"><b>추출한 글자 확인 · 수정</b><small>AI가 잘못 읽은 부분이 있을 수 있습니다. 확인하고 고친 뒤 원문에 넣으세요. 원문이 바뀌면 기존 AI 요약·분석은 다시 실행해야 합니다.</small><textarea aria-label="추출한 글자" value={ocr.text} onChange={e=>setOcr({...ocr,text:e.target.value})}/><div className="capture-buttons"><button type="button" className="button primary" disabled={saving||!ocr.text.trim()} onClick={()=>void insert("append")}>원문 끝에 추가</button><button type="button" className="button soft" disabled={saving||!ocr.text.trim()} onClick={()=>{if(window.confirm("기존 회의 원문을 지우고 사진 내용으로 바꿀까요?"))void insert("replace");}}>원문 바꾸기</button><button type="button" className="button ghost" disabled={saving} onClick={()=>setOcr(null)}>취소</button></div></div>}
    {documents.map(item=><p className="photo-doc" key={item.id}><b>{item.file_name}</b><small> · {item.author}</small><button type="button" className="button ghost" onClick={()=>void downloadAttachment(fileUrl(item.id),item.file_name||"file").catch(e=>onNotify(e.message))}>다운로드</button>{(canManage||item.uploaded_by===userId)&&<button type="button" className="icon-control" title="삭제" aria-label={`${item.file_name} 삭제`} onClick={()=>void remove(item)}><Trash2/></button>}</p>)}
    {!list.isLoading&&!files.length&&<p className="photo-hint">아직 올린 사진이 없습니다.</p>}
  </section>;
}
