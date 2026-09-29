import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MarkdownContent({content,className=""}:{content:string;className?:string}) {
  return <div className={`markdown-body ${className}`}><ReactMarkdown remarkPlugins={[remarkGfm]} components={{a:({children,...props})=><a {...props} target="_blank" rel="noreferrer">{children}</a>}}>{content}</ReactMarkdown></div>;
}
