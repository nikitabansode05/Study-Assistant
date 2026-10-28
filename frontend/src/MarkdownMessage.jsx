import { memo, useState } from 'react'
import ReactMarkdown, { defaultUrlTransform } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Check, Copy } from 'lucide-react'

// Only these URL schemes are allowed in links. Everything else (javascript:, data:, vbscript:, ...)
// is removed. defaultUrlTransform already strips dangerous protocols; this is a stricter allow-list.
const SAFE_URL = /^(https?:|mailto:|#|\/(?!\/))/i

function safeUrl(url) {
  const cleaned = defaultUrlTransform(url || '')
  return cleaned && SAFE_URL.test(cleaned) ? cleaned : ''
}

function textOf(node) {
  if (node == null || typeof node === 'boolean') return ''
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textOf).join('')
  return textOf(node.props?.children)
}

function CodeBlock({ children }) {
  const [copied, setCopied] = useState(false)
  const codeEl = Array.isArray(children) ? children[0] : children
  const language = /language-([\w+#-]+)/.exec(codeEl?.props?.className || '')?.[1]
  const code = textOf(codeEl).replace(/\n$/, '')

  async function copy() {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch { /* clipboard unavailable (e.g. non-secure origin) */ }
  }

  return (
    <div className="md-code">
      <div className="md-code-bar">
        <span>{language || 'code'}</span>
        <button type="button" onClick={copy} aria-label="Copy code">
          {copied ? <><Check size={12}/> Copied</> : <><Copy size={12}/> Copy</>}
        </button>
      </div>
      <pre>{children}</pre>
    </div>
  )
}

const components = {
  a: ({ href, children }) => href
    ? <a href={href} target="_blank" rel="noopener noreferrer nofollow">{children}</a>
    : <span>{children}</span>,
  // Remote images in model output are not loaded (privacy / tracking); show the alt text instead.
  img: ({ alt }) => <span className="md-image-placeholder">[image{alt ? `: ${alt}` : ''}]</span>,
  pre: CodeBlock,
  table: ({ children }) => <div className="md-table-wrap"><table>{children}</table></div>,
}

/**
 * Renders assistant output as GitHub Flavored Markdown.
 * - No dangerouslySetInnerHTML; raw HTML in the model output is skipped (skipHtml).
 * - Link URLs are restricted to http(s), mailto and relative/anchor links.
 */
function MarkdownMessage({ content }) {
  const text = typeof content === 'string' ? content : String(content ?? '')
  if (!text.trim()) return <div className="markdown-body"><p><em>(No answer text was returned.)</em></p></div>
  return (
    <div className="markdown-body">
      <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml urlTransform={safeUrl} components={components}>
        {text}
      </ReactMarkdown>
    </div>
  )
}

export default memo(MarkdownMessage)
