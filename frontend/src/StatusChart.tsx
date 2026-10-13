const colors:Record<string,string>={in_progress:"#3478ff",todo:"#ffac55",done:"#0cbea0",cancelled:"#c9cce0"};
export default function StatusChart({groups}:{groups:{key:string;label:string;count:number}[]}) {
  const total=groups.reduce((sum,g)=>sum+g.count,0);
  const radius=70;const length=2*Math.PI*radius;let offset=0;
  return <div className="native-status-chart"><svg viewBox="0 0 200 200" role="img" aria-label={`업무 현황: ${groups.map(g=>`${g.label} ${g.count}개`).join(", ")}`}>
    <circle cx="100" cy="100" r={radius} fill="none" stroke="#edf0f7" strokeWidth="22"/>
    {groups.filter(g=>g.count>0).map(g=>{const arc=g.count/total*length;const start=offset;offset+=arc;return <circle key={g.key} cx="100" cy="100" r={radius} fill="none" stroke={colors[g.key]} strokeWidth="22" strokeDasharray={`${arc} ${length-arc}`} strokeDashoffset={-start} transform="rotate(-90 100 100)"><title>{g.label} {g.count}개</title></circle>;})}
    <text x="100" y="100" textAnchor="middle" dominantBaseline="middle" fill="currentColor" fontSize="30" fontWeight="700">{total}</text><text x="100" y="125" textAnchor="middle" fill="#737b99" fontSize="12">전체 업무</text>
    </svg><ul>{groups.map(g=><li key={g.key}><span><i style={{background:colors[g.key]}}/>{g.label}</span><b>{g.count}개</b></li>)}</ul>{!total&&<p>등록된 업무가 없습니다.</p>}</div>;
}
