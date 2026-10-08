interface Group { key:string; label:string; count:number; }
export default function StreamlitStatusChart({groups}:{groups:Group[]}) {
 const url=new URL(import.meta.env.VITE_STREAMLIT_URL||`${window.location.protocol}//${window.location.hostname}:8501/`,window.location.origin);
 url.searchParams.set("embed","true");
 groups.forEach(group=>url.searchParams.set(group.key,String(group.count)));
 return <iframe title={`업무 현황: ${groups.map(g=>`${g.label} ${g.count}개`).join(", ")}`} src={url.toString()} style={{width:"100%",height:330,border:0}}/>;
}
