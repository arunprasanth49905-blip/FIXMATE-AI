import React, { useState, useRef } from 'react';
import {
  Plus,
  FolderPlus,
  Upload,
  ChevronRight,
  ChevronDown,
  Trash2,
  Edit2,
  Folder,
} from 'lucide-react';
import { FileTreeItem } from '../../types/api';
import { FileIcon } from './FileIcon';

interface FileExplorerProps {
  files: FileTreeItem[];
  activeFileId: string | null;
  onSelectFile: (file: FileTreeItem) => void;
  onCreateFile: (parentPath?: string) => void;
  onCreateFolder: (parentPath?: string) => void;
  onRenameItem: (item: FileTreeItem) => void;
  onDeleteItem: (item: FileTreeItem) => void;
  onUploadFiles: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export const FileExplorer: React.FC<FileExplorerProps> = ({
  files,
  activeFileId,
  onSelectFile,
  onCreateFile,
  onCreateFolder,
  onRenameItem,
  onDeleteItem,
  onUploadFiles,
}) => {
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});
  const uploadInputRef = useRef<HTMLInputElement>(null);

  const toggleFolder = (path: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedFolders((prev) => ({
      ...prev,
      [path]: !prev[path],
    }));
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const renderTree = (items: FileTreeItem[], depth = 0) => {
    return items.map((item) => {
      const isExpanded = !!expandedFolders[item.path];
      const isActive = item.id === activeFileId;

      if (item.is_directory) {
        return (
          <div key={item.id}>
            <div
              className={`tree-node ${isActive ? 'active' : ''}`}
              style={{ paddingLeft: `${8 + depth * 14}px` }}
              onClick={(e) => toggleFolder(item.path, e)}
            >
              <div className="tree-node-content">
                <span style={{ display: 'inline-flex', alignItems: 'center', color: 'var(--color-navy-400)' }}>
                  {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </span>
                <FileIcon name={item.name} is_directory isOpen={isExpanded} size={15} />
                <span>{item.name}</span>
              </div>

              <div className="tree-node-actions" onClick={(e) => e.stopPropagation()}>
                <button
                  type="button"
                  className="icon-btn"
                  title="New File Inside"
                  onClick={() => onCreateFile(item.path)}
                >
                  <Plus size={13} />
                </button>
                <button
                  type="button"
                  className="icon-btn"
                  title="New Folder Inside"
                  onClick={() => onCreateFolder(item.path)}
                >
                  <FolderPlus size={13} />
                </button>
                <button
                  type="button"
                  className="icon-btn"
                  title="Rename Folder"
                  onClick={() => onRenameItem(item)}
                >
                  <Edit2 size={12} />
                </button>
                <button
                  type="button"
                  className="icon-btn"
                  title="Delete Folder"
                  style={{ color: 'var(--color-red-danger)' }}
                  onClick={() => onDeleteItem(item)}
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>

            {isExpanded && item.children && item.children.length > 0 && (
              <div>{renderTree(item.children, depth + 1)}</div>
            )}
          </div>
        );
      }

      // File item
      return (
        <div
          key={item.id}
          className={`tree-node ${isActive ? 'active' : ''}`}
          style={{ paddingLeft: `${24 + depth * 14}px` }}
          onClick={() => onSelectFile(item)}
        >
          <div className="tree-node-content">
            <FileIcon name={item.name} size={15} />
            <span title={item.path}>{item.name}</span>
            {item.size > 0 && (
              <span style={{ fontSize: '11px', color: 'var(--color-navy-400)', fontFamily: 'var(--font-mono)' }}>
                {formatFileSize(item.size)}
              </span>
            )}
          </div>

          <div className="tree-node-actions" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="icon-btn"
              title="Rename File"
              onClick={() => onRenameItem(item)}
            >
              <Edit2 size={12} />
            </button>
            <button
              type="button"
              className="icon-btn"
              title="Delete File"
              style={{ color: 'var(--color-red-danger)' }}
              onClick={() => onDeleteItem(item)}
            >
              <Trash2 size={12} />
            </button>
          </div>
        </div>
      );
    });
  };

  return (
    <aside className="file-explorer">
      <div className="file-explorer-header">
        <span>Files</span>
        <div className="file-explorer-actions">
          <button
            type="button"
            data-testid="new-file-button"
            className="icon-btn"
            title="Create New File"
            onClick={() => onCreateFile()}
          >
            <Plus size={15} />
          </button>
          <button
            type="button"
            className="icon-btn"
            title="Create New Folder"
            onClick={() => onCreateFolder()}
          >
            <FolderPlus size={15} />
          </button>
          <button
            type="button"
            className="icon-btn"
            title="Upload Files"
            onClick={() => uploadInputRef.current?.click()}
          >
            <Upload size={14} />
          </button>
          <input
            type="file"
            ref={uploadInputRef}
            style={{ display: 'none' }}
            multiple
            onChange={onUploadFiles}
          />
        </div>
      </div>

      <div className="file-tree-container">
        {files.length === 0 ? (
          <div style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--color-navy-400)' }}>
            <Folder size={28} style={{ margin: '0 auto 8px', opacity: 0.5 }} />
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-navy-700)', marginBottom: '4px' }}>
              No Files Found
            </div>
            <p style={{ fontSize: '11.5px', lineHeight: 1.4, marginBottom: '12px' }}>
              Add files, create directories, or upload source files to start working.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => onCreateFile()}
                style={{ fontSize: '12px', justifyContent: 'center' }}
              >
                <Plus size={13} /> Add File
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => uploadInputRef.current?.click()}
                style={{ fontSize: '12px', justifyContent: 'center' }}
              >
                <Upload size={13} /> Upload Files
              </button>
            </div>
          </div>
        ) : (
          renderTree(files)
        )}
      </div>
    </aside>
  );
};
