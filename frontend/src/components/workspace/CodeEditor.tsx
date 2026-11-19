import React from 'react';
import Editor from '@monaco-editor/react';
import { AlertCircle, Lock } from 'lucide-react';

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  fileName: string;
  isBinary?: boolean;
  isLoading?: boolean;
  error?: string | null;
}

export const CodeEditor: React.FC<CodeEditorProps> = ({
  value,
  onChange,
  fileName,
  isBinary = false,
  isLoading = false,
  error = null,
}) => {
  const getLanguage = (name: string): string => {
    const ext = name.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'py':
      case 'pyw':
        return 'python';
      case 'js':
      case 'jsx':
      case 'mjs':
      case 'cjs':
        return 'javascript';
      case 'ts':
      case 'tsx':
        return 'typescript';
      case 'json':
        return 'json';
      case 'md':
      case 'markdown':
        return 'markdown';
      case 'html':
      case 'htm':
        return 'html';
      case 'css':
      case 'scss':
      case 'sass':
        return 'css';
      case 'sql':
        return 'sql';
      case 'sh':
      case 'bash':
        return 'shell';
      case 'yaml':
      case 'yml':
        return 'yaml';
      case 'xml':
        return 'xml';
      default:
        return 'plaintext';
    }
  };

  if (isLoading) {
    return (
      <div className="editor-empty-state">
        <div style={{ color: 'var(--color-navy-500)', fontSize: '13px' }}>
          Loading file content...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="editor-empty-state">
        <AlertCircle size={32} style={{ color: 'var(--color-red-danger)', marginBottom: '10px' }} />
        <div style={{ fontWeight: 600, color: 'var(--color-red-danger)', marginBottom: '4px' }}>
          Failed to load file
        </div>
        <div style={{ fontSize: '12.5px', color: 'var(--color-navy-600)' }}>{error}</div>
      </div>
    );
  }

  if (isBinary) {
    return (
      <div className="editor-empty-state">
        <Lock size={32} style={{ color: 'var(--color-navy-400)', marginBottom: '10px' }} />
        <div style={{ fontWeight: 600, color: 'var(--color-navy-800)', marginBottom: '4px' }}>
          Binary or Unsupported File Format
        </div>
        <div style={{ fontSize: '12.5px', color: 'var(--color-navy-500)', maxWidth: '400px' }}>
          {value || 'This file cannot be displayed or edited in the text editor.'}
        </div>
      </div>
    );
  }

  return (
    <div className="monaco-wrapper">
      <Editor
        height="100%"
        language={getLanguage(fileName)}
        value={value}
        theme="vs-light"
        onChange={(val) => onChange(val || '')}
        options={{
          fontSize: 13.5,
          fontFamily: "'JetBrains Mono', Consolas, 'Courier New', monospace",
          minimap: { enabled: true },
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          wordWrap: 'on',
          tabSize: 4,
          renderWhitespace: 'selection',
          padding: { top: 12, bottom: 12 },
        }}
        loading={
          <div style={{ padding: '20px', color: 'var(--color-navy-500)', fontSize: '13px' }}>
            Initializing Monaco Editor...
          </div>
        }
      />
    </div>
  );
};
