import { useState } from 'react';
import { motion } from 'framer-motion';
import { Copy, Check, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

// Simple markdown parser for common elements
export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const handleCopyCode = async (code: string, id: string) => {
    await navigator.clipboard.writeText(code);
    setCopiedCode(id);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  // Parse and render markdown content
  const renderContent = (text: string) => {
    const lines = text.split('\n');
    const elements: JSX.Element[] = [];
    let i = 0;
    let key = 0;

    while (i < lines.length) {
      const line = lines[i];

      // Code blocks (```language\ncode\n```)
      if (line.startsWith('```')) {
        const language = line.slice(3).trim() || 'text';
        const codeLines: string[] = [];
        i++;
        while (i < lines.length && !lines[i].startsWith('```')) {
          codeLines.push(lines[i]);
          i++;
        }
        const code = codeLines.join('\n');
        const codeKey = `code-${key++}`;
        
        elements.push(
          <CodeBlock
            key={codeKey}
            code={code}
            language={language}
            onCopy={() => handleCopyCode(code, codeKey)}
            isCopied={copiedCode === codeKey}
          />
        );
        i++;
        continue;
      }

      // Inline code (`code`)
      if (line.includes('`')) {
        const parts = line.split(/(`[^`]+`)/);
        const renderedParts = parts.map((part, idx) => {
          if (part.startsWith('`') && part.endsWith('`')) {
            const code = part.slice(1, -1);
            return (
              <code 
                key={idx} 
                className="px-1.5 py-0.5 bg-gray-100 text-gray-800 rounded text-sm font-mono"
              >
                {code}
              </code>
            );
          }
          return <span key={idx}>{part}</span>;
        });
        elements.push(<p key={key++} className="my-2">{renderedParts}</p>);
        i++;
        continue;
      }

      // Headers
      if (line.startsWith('### ')) {
        elements.push(
          <h3 key={key++} className="text-lg font-semibold text-gray-900 mt-4 mb-2">
            {line.slice(4)}
          </h3>
        );
        i++;
        continue;
      }
      if (line.startsWith('## ')) {
        elements.push(
          <h2 key={key++} className="text-xl font-semibold text-gray-900 mt-5 mb-3">
            {line.slice(3)}
          </h2>
        );
        i++;
        continue;
      }
      if (line.startsWith('# ')) {
        elements.push(
          <h1 key={key++} className="text-2xl font-bold text-gray-900 mt-6 mb-4">
            {line.slice(2)}
          </h1>
        );
        i++;
        continue;
      }

      // Blockquotes
      if (line.startsWith('> ')) {
        const quoteLines: string[] = [line.slice(2)];
        i++;
        while (i < lines.length && lines[i].startsWith('> ')) {
          quoteLines.push(lines[i].slice(2));
          i++;
        }
        elements.push(
          <blockquote 
            key={key++} 
            className="border-l-4 border-indigo-300 pl-4 py-2 my-3 bg-indigo-50/50 italic text-gray-700"
          >
            {quoteLines.join('\n')}
          </blockquote>
        );
        continue;
      }

      // Horizontal rule
      if (line === '---' || line === '***' || line === '___') {
        elements.push(<hr key={key++} className="my-4 border-gray-200" />);
        i++;
        continue;
      }

      // Unordered lists
      if (line.match(/^[-*+]\s/)) {
        const items: string[] = [];
        while (i < lines.length && lines[i].match(/^[-*+]\s/)) {
          items.push(lines[i].replace(/^[-*+]\s/, ''));
          i++;
        }
        elements.push(
          <ul key={key++} className="list-disc list-inside my-3 space-y-1">
            {items.map((item, idx) => (
              <li key={idx} className="text-gray-700">{renderInlineMarkdown(item)}</li>
            ))}
          </ul>
        );
        continue;
      }

      // Ordered lists
      if (line.match(/^\d+\.\s/)) {
        const items: string[] = [];
        while (i < lines.length && lines[i].match(/^\d+\.\s/)) {
          items.push(lines[i].replace(/^\d+\.\s/, ''));
          i++;
        }
        elements.push(
          <ol key={key++} className="list-decimal list-inside my-3 space-y-1">
            {items.map((item, idx) => (
              <li key={idx} className="text-gray-700">{renderInlineMarkdown(item)}</li>
            ))}
          </ol>
        );
        continue;
      }

      // Empty lines
      if (line.trim() === '') {
        elements.push(<div key={key++} className="h-2" />);
        i++;
        continue;
      }

      // Regular paragraphs with inline formatting
      elements.push(
        <p key={key++} className="my-2 text-gray-700 leading-relaxed">
          {renderInlineMarkdown(line)}
        </p>
      );
      i++;
    }

    return elements;
  };

  // Render inline markdown (bold, italic, links)
  const renderInlineMarkdown = (text: string) => {
    // Process links [text](url)
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    const boldRegex = /\*\*([^*]+)\*\*/g;
    const italicRegex = /\*([^*]+)\*/g;
    const strikethroughRegex = /~~([^~]+)~~/g;

    // Split by links first
    const parts: (string | JSX.Element)[] = [];
    let lastIndex = 0;
    let match;

    while ((match = linkRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index));
      }
      parts.push(
        <a
          key={match.index}
          href={match[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-indigo-600 hover:text-indigo-700 underline inline-flex items-center gap-0.5"
        >
          {match[1]}
          <ExternalLink className="w-3 h-3" />
        </a>
      );
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex));
    }

    // Process bold, italic, strikethrough in text parts
    return parts.map((part, idx) => {
      if (typeof part !== 'string') return part;

      let processed = part;
      
      // Bold
      processed = processed.replace(boldRegex, '<strong>$1</strong>');
      // Italic
      processed = processed.replace(italicRegex, '<em>$1</em>');
      // Strikethrough
      processed = processed.replace(strikethroughRegex, '<del>$1</del>');

      // Convert to React elements
      const elements: (string | JSX.Element)[] = [];
      const htmlRegex = /<(\/?)(strong|em|del)>/g;
      let htmlLastIndex = 0;
      let htmlMatch;
      const tagStack: { tag: string; start: number }[] = [];

      while ((htmlMatch = htmlRegex.exec(processed)) !== null) {
        if (htmlMatch.index > htmlLastIndex) {
          elements.push(processed.slice(htmlLastIndex, htmlMatch.index));
        }

        const isClosing = htmlMatch[1] === '/';
        const tag = htmlMatch[2];

        if (isClosing && tagStack.length > 0 && tagStack[tagStack.length - 1].tag === tag) {
          const start = tagStack.pop()!.start;
          const content = elements.splice(start).join('');
          
          if (tag === 'strong') {
            elements.push(<strong key={`${idx}-${htmlMatch.index}`} className="font-semibold">{content}</strong>);
          } else if (tag === 'em') {
            elements.push(<em key={`${idx}-${htmlMatch.index}`} className="italic">{content}</em>);
          } else if (tag === 'del') {
            elements.push(<del key={`${idx}-${htmlMatch.index}`} className="line-through text-gray-500">{content}</del>);
          }
        } else if (!isClosing) {
          tagStack.push({ tag, start: elements.length });
        }

        htmlLastIndex = htmlMatch.index + htmlMatch[0].length;
      }

      if (htmlLastIndex < processed.length) {
        elements.push(processed.slice(htmlLastIndex));
      }

      return <span key={idx}>{elements}</span>;
    });
  };

  return (
    <div className={cn('markdown-content', className)}>
      {renderContent(content)}
    </div>
  );
}

// Code block component
interface CodeBlockProps {
  code: string;
  language: string;
  onCopy: () => void;
  isCopied: boolean;
}

function CodeBlock({ code, language, onCopy, isCopied }: CodeBlockProps) {
  const languageColors: Record<string, string> = {
    javascript: 'bg-yellow-100 text-yellow-700',
    typescript: 'bg-blue-100 text-blue-700',
    python: 'bg-blue-100 text-blue-700',
    java: 'bg-orange-100 text-orange-700',
    cpp: 'bg-purple-100 text-purple-700',
    c: 'bg-purple-100 text-purple-700',
    go: 'bg-cyan-100 text-cyan-700',
    rust: 'bg-orange-100 text-orange-700',
    bash: 'bg-gray-100 text-gray-700',
    shell: 'bg-gray-100 text-gray-700',
    sql: 'bg-emerald-100 text-emerald-700',
    html: 'bg-orange-100 text-orange-700',
    css: 'bg-blue-100 text-blue-700',
    json: 'bg-gray-100 text-gray-700',
    yaml: 'bg-gray-100 text-gray-700',
    markdown: 'bg-gray-100 text-gray-700',
    text: 'bg-gray-100 text-gray-700',
  };

  return (
    <div className="my-4 rounded-lg overflow-hidden border border-gray-200">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200">
        <span className={cn(
          'px-2 py-0.5 rounded text-xs font-medium uppercase',
          languageColors[language.toLowerCase()] || 'bg-gray-100 text-gray-600'
        )}>
          {language}
        </span>
        <button
          onClick={onCopy}
          className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded transition-colors"
        >
          {isCopied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-500" />
              <span className="text-emerald-600">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      
      {/* Code */}
      <pre className="p-4 bg-gray-900 overflow-x-auto">
        <code className="text-sm font-mono text-gray-100 whitespace-pre">
          {code}
        </code>
      </pre>
    </div>
  );
}

// Table renderer for markdown tables
interface TableData {
  headers: string[];
  rows: string[][];
}

export function MarkdownTable({ headers, rows }: TableData) {
  return (
    <div className="my-4 overflow-x-auto">
      <table className="min-w-full border border-gray-200 rounded-lg overflow-hidden">
        <thead className="bg-gray-50">
          <tr>
            {headers.map((header, i) => (
              <th 
                key={i} 
                className="px-4 py-2 text-left text-sm font-semibold text-gray-700 border-b border-gray-200"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="bg-white hover:bg-gray-50">
              {row.map((cell, j) => (
                <td 
                  key={j} 
                  className="px-4 py-2 text-sm text-gray-700 border-b border-gray-200"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
