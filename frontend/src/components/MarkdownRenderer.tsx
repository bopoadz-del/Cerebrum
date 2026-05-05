import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

// Escape all HTML special characters in a raw string before markdown transforms.
// This prevents XSS: user-supplied content is never interpreted as HTML.
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  const parseMarkdown = (text: string): string => {
    // 1. Split on fenced code blocks first so their contents are escaped verbatim
    const parts = text.split(/(```[\w]*\n[\s\S]*?```)/g);
    const processed = parts.map((part, i) => {
      if (i % 2 === 1) {
        // Fenced code block — escape content, preserve structure
        const match = part.match(/^```(\w*)\n([\s\S]*)```$/);
        const code = match ? escapeHtml(match[2]) : escapeHtml(part);
        return `<pre class="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto my-2"><code>${code}</code></pre>`;
      }
      // For normal text: escape first, then apply markdown patterns
      let html = escapeHtml(part)
        // Inline code (backtick contents already escaped)
        .replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">$1</code>')
        // Headers
        .replace(/^### (.*$)/gim, '<h3 class="text-lg font-bold mb-2 mt-4">$1</h3>')
        .replace(/^## (.*$)/gim, '<h2 class="text-xl font-bold mb-2 mt-4">$1</h2>')
        .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mb-2 mt-4">$1</h1>')
        // Bold and italic
        .replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Links — href is already escaped by escapeHtml above
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-indigo-600 hover:underline" target="_blank" rel="noopener noreferrer">$1</a>')
        // Lists
        .replace(/^\* (.*$)/gim, '<li class="ml-4">$1</li>')
        .replace(/^- (.*$)/gim, '<li class="ml-4">$1</li>')
        .replace(/^\d+\. (.*$)/gim, '<li class="ml-4">$1</li>')
        // Blockquotes
        .replace(/^&gt; (.*$)/gim, '<blockquote class="border-l-4 border-gray-300 pl-4 italic my-2">$1</blockquote>')
        // Horizontal rule
        .replace(/^---+$/gim, '<hr class="my-4 border-gray-200" />')
        // Paragraphs / line breaks
        .replace(/\n\n/g, '</p><p class="mb-2">')
        .replace(/\n/g, '<br />');
      return '<p class="mb-2">' + html + '</p>';
    });
    return processed.join('');
  };

  return (
    <div
      className={cn('prose prose-sm max-w-none', className)}
      dangerouslySetInnerHTML={{ __html: parseMarkdown(content) }}
    />
  );
}

