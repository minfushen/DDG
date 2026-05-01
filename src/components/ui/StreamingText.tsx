// ========================================
// StreamingText — 流式文本渲染组件
// 支持 token-by-token 渲染效果
// ========================================

import { useState, useEffect, useRef, useCallback } from 'react';

export interface StreamingTextProps {
  /** 完整内容 */
  content: string;
  /** 是否正在流式输出 */
  isStreaming: boolean;
  /** 渲染速度 (tokens per second) */
  speed?: number;
  /** 光标样式 */
  cursorStyle?: 'block' | 'line' | 'none';
  /** 完成回调 */
  onComplete?: () => void;
  /** 自定义类名 */
  className?: string;
  /** 是否启用打字机效果 */
  typewriter?: boolean;
}

export function StreamingText({
  content,
  isStreaming,
  speed = 30,
  cursorStyle = 'block',
  onComplete,
  className = '',
  typewriter = true,
}: StreamingTextProps) {
  const [displayedContent, setDisplayedContent] = useState('');
  const [isComplete, setIsComplete] = useState(false);
  const animationRef = useRef<{ index: number; timer: ReturnType<typeof setInterval> | null }>({
    index: 0,
    timer: null,
  });

  // 清理定时器
  const clearTimer = useCallback(() => {
    if (animationRef.current.timer) {
      clearInterval(animationRef.current.timer);
      animationRef.current.timer = null;
    }
  }, []);

  // 流式渲染
  useEffect(() => {
    // 非流式模式，直接显示完整内容
    if (!typewriter || !isStreaming) {
      setDisplayedContent(content);
      setIsComplete(!isStreaming);
      if (!isStreaming && content) {
        onComplete?.();
      }
      return;
    }

    // 重置状态
    if (animationRef.current.index === 0) {
      setDisplayedContent('');
    }

    // 计算每帧渲染的字符数
    const charsPerFrame = Math.max(1, Math.floor(speed / 10));

    animationRef.current.timer = setInterval(() => {
      const nextIndex = animationRef.current.index + charsPerFrame;

      if (nextIndex >= content.length) {
        // 渲染完成
        setDisplayedContent(content);
        setIsComplete(true);
        clearTimer();
        onComplete?.();
      } else {
        // 增量渲染
        setDisplayedContent(content.slice(0, nextIndex));
        animationRef.current.index = nextIndex;
      }
    }, 100);

    return () => clearTimer();
  }, [content, isStreaming, speed, typewriter, clearTimer, onComplete]);

  // 重置索引
  useEffect(() => {
    if (isStreaming) {
      animationRef.current.index = 0;
      setIsComplete(false);
    }
  }, [isStreaming]);

  // 光标组件
  const Cursor = () => {
    if (!isStreaming || isComplete || cursorStyle === 'none') return null;

    const cursorClass = cursorStyle === 'block'
      ? 'inline-block w-2 h-4 bg-blue-500 animate-pulse ml-0.5'
      : 'inline-block w-0.5 h-4 bg-blue-500 animate-pulse ml-0.5';

    return <span className={cursorClass} />;
  };

  return (
    <div className={`text-sm text-gray-700 whitespace-pre-wrap ${className}`}>
      {displayedContent}
      <Cursor />
    </div>
  );
}

// ── 流式 Markdown 渲染 ─────────────────────────────────

export interface StreamingMarkdownProps extends StreamingTextProps {
  /** 是否渲染 Markdown */
  renderMarkdown?: boolean;
}

export function StreamingMarkdown({
  content,
  isStreaming,
  speed = 30,
  cursorStyle = 'block',
  onComplete,
  className = '',
}: StreamingMarkdownProps) {
  const [displayedContent, setDisplayedContent] = useState('');
  const animationRef = useRef<{ index: number; timer: ReturnType<typeof setInterval> | null }>({
    index: 0,
    timer: null,
  });

  const clearTimer = useCallback(() => {
    if (animationRef.current.timer) {
      clearInterval(animationRef.current.timer);
      animationRef.current.timer = null;
    }
  }, []);

  useEffect(() => {
    if (!isStreaming) {
      setDisplayedContent(content);
      clearTimer();
      if (content) onComplete?.();
      return;
    }

    if (animationRef.current.index === 0) {
      setDisplayedContent('');
    }

    const charsPerFrame = Math.max(1, Math.floor(speed / 10));

    animationRef.current.timer = setInterval(() => {
      const nextIndex = animationRef.current.index + charsPerFrame;

      if (nextIndex >= content.length) {
        setDisplayedContent(content);
        clearTimer();
        onComplete?.();
      } else {
        setDisplayedContent(content.slice(0, nextIndex));
        animationRef.current.index = nextIndex;
      }
    }, 100);

    return () => clearTimer();
  }, [content, isStreaming, speed, clearTimer, onComplete]);

  useEffect(() => {
    if (isStreaming) {
      animationRef.current.index = 0;
    }
  }, [isStreaming]);

  // 简化的 Markdown 渲染（实际应使用 react-markdown）
  const renderContent = (text: string) => {
    return text.split('\n').map((line, i) => {
      // 标题
      if (line.startsWith('### ')) {
        return <h4 key={i} className="font-semibold text-gray-800 mt-3 mb-1">{line.slice(4)}</h4>;
      }
      if (line.startsWith('## ')) {
        return <h3 key={i} className="font-bold text-gray-800 mt-4 mb-2">{line.slice(3)}</h3>;
      }
      if (line.startsWith('# ')) {
        return <h2 key={i} className="font-bold text-gray-900 text-lg mt-4 mb-2">{line.slice(2)}</h2>;
      }

      // 列表
      if (line.startsWith('- ') || line.startsWith('* ')) {
        return <li key={i} className="ml-4 text-gray-700">{line.slice(2)}</li>;
      }

      // 粗体
      const boldText = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      if (boldText !== line) {
        return <p key={i} className="text-gray-700" dangerouslySetInnerHTML={{ __html: boldText }} />;
      }

      // 普通文本
      if (line.trim()) {
        return <p key={i} className="text-gray-700">{line}</p>;
      }

      return null;
    });
  };

  return (
    <div className={`prose prose-sm max-w-none ${className}`}>
      {renderContent(displayedContent)}
      {isStreaming && cursorStyle !== 'none' && (
        <span className="inline-block w-2 h-4 bg-blue-500 animate-pulse ml-0.5" />
      )}
    </div>
  );
}

// ── 流式代码块渲染 ─────────────────────────────────────

export interface StreamingCodeProps {
  code: string;
  language?: string;
  isStreaming: boolean;
  speed?: number;
  showLineNumbers?: boolean;
  className?: string;
}

export function StreamingCode({
  code,
  language = 'typescript',
  isStreaming,
  speed = 50,
  showLineNumbers = true,
  className = '',
}: StreamingCodeProps) {
  const [displayedCode, setDisplayedCode] = useState('');
  const animationRef = useRef<{ index: number; timer: ReturnType<typeof setInterval> | null }>({
    index: 0,
    timer: null,
  });

  const clearTimer = useCallback(() => {
    if (animationRef.current.timer) {
      clearInterval(animationRef.current.timer);
      animationRef.current.timer = null;
    }
  }, []);

  useEffect(() => {
    if (!isStreaming) {
      setDisplayedCode(code);
      clearTimer();
      return;
    }

    if (animationRef.current.index === 0) {
      setDisplayedCode('');
    }

    const charsPerFrame = Math.max(1, Math.floor(speed / 10));

    animationRef.current.timer = setInterval(() => {
      const nextIndex = animationRef.current.index + charsPerFrame;

      if (nextIndex >= code.length) {
        setDisplayedCode(code);
        clearTimer();
      } else {
        setDisplayedCode(code.slice(0, nextIndex));
        animationRef.current.index = nextIndex;
      }
    }, 100);

    return () => clearTimer();
  }, [code, isStreaming, speed, clearTimer]);

  useEffect(() => {
    if (isStreaming) {
      animationRef.current.index = 0;
    }
  }, [isStreaming]);

  const lines = displayedCode.split('\n');

  return (
    <div className={`bg-gray-900 rounded-xl overflow-hidden ${className}`}>
      {/* 头部 */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-500" />
          <span className="w-3 h-3 rounded-full bg-yellow-500" />
          <span className="w-3 h-3 rounded-full bg-green-500" />
        </div>
        <span className="text-xs text-gray-400 font-mono">{language}</span>
      </div>

      {/* 代码区 */}
      <div className="p-4 overflow-x-auto">
        <pre className="text-sm font-mono">
          <code className="text-gray-300">
            {lines.map((line, i) => (
              <div key={i} className="flex">
                {showLineNumbers && (
                  <span className="w-8 text-gray-500 select-none text-right pr-4">{i + 1}</span>
                )}
                <span>{line}</span>
              </div>
            ))}
          </code>
        </pre>
      </div>
    </div>
  );
}
