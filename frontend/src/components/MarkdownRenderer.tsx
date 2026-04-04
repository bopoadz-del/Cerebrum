import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={cn('prose prose-sm max-w-none', className)}>
      <ReactMarkdown
        components={{
          code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '');
            return !inline && match ? (
              <SyntaxHighlighter
                style={oneDark}
                language={match[1]}
                PreTag="div"
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code className={cn('bg-gray-100 px-1 py-0.5 rounded text-sm', className)} {...props}>
                {children}
              </code>
            );
          },
          p({ children }: { children: React.ReactNode }) {
            return <p className="mb-2 last:mb-0">{children}</p>;
          },
          ul({ children }: { children: React.ReactNode }) {
            return <ul className="list-disc pl-4 mb-2">{children}</ul>;
          },
          ol({ children }: { children: React.ReactNode }) {
            return <ol className="list-decimal pl-4 mb-2">{children}</ol>;
          },
          li({ children }: { children: React.ReactNode }) {
            return <li className="mb-1">{children}</li>;
          },
          h1({ children }: { children: React.ReactNode }) {
            return <h1 className="text-xl font-bold mb-2">{children}</h1>;
          },
          h2({ children }: { children: React.ReactNode }) {
            return <h2 className="text-lg font-bold mb-2">{children}</h2>;
          },
          h3({ children }: { children: React.ReactNode }) {
            return <h3 className="text-base font-bold mb-2">{children}</h3>;
          },
          blockquote({ children }: { children: React.ReactNode }) {
            return <blockquote className="border-l-4 border-gray-300 pl-4 italic mb-2">{children}</blockquote>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
