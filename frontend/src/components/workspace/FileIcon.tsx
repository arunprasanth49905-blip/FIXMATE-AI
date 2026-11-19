import React from 'react';
import {
  FileCode2,
  FileJson,
  FileText,
  File,
  Folder,
  FolderOpen,
  Code2,
  Terminal,
} from 'lucide-react';

interface FileIconProps {
  name: string;
  is_directory?: boolean;
  isOpen?: boolean;
  size?: number;
}

export const FileIcon: React.FC<FileIconProps> = ({
  name,
  is_directory = false,
  isOpen = false,
  size = 15,
}) => {
  if (is_directory) {
    return isOpen ? (
      <FolderOpen size={size} style={{ color: 'var(--color-blue-primary)', flexShrink: 0 }} />
    ) : (
      <Folder size={size} style={{ color: 'var(--color-navy-500)', flexShrink: 0 }} />
    );
  }

  const ext = name.split('.').pop()?.toLowerCase();

  switch (ext) {
    case 'py':
    case 'pyw':
      return <Terminal size={size} style={{ color: '#3b82f6', flexShrink: 0 }} />;
    case 'js':
    case 'jsx':
    case 'mjs':
    case 'cjs':
      return <FileCode2 size={size} style={{ color: '#eab308', flexShrink: 0 }} />;
    case 'ts':
    case 'tsx':
      return <Code2 size={size} style={{ color: '#0284c7', flexShrink: 0 }} />;
    case 'json':
      return <FileJson size={size} style={{ color: '#10b981', flexShrink: 0 }} />;
    case 'md':
    case 'markdown':
    case 'txt':
      return <FileText size={size} style={{ color: '#64748b', flexShrink: 0 }} />;
    default:
      return <File size={size} style={{ color: '#94a3b8', flexShrink: 0 }} />;
  }
};
