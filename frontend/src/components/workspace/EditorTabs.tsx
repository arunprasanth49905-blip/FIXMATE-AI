import React from 'react';
import { X } from 'lucide-react';
import { FileIcon } from './FileIcon';

export interface OpenTab {
  id: string;
  path: string;
  name: string;
  isDirty?: boolean;
}

interface EditorTabsProps {
  tabs: OpenTab[];
  activeTabId: string | null;
  onSelectTab: (tabId: string) => void;
  onCloseTab: (tabId: string, e: React.MouseEvent) => void;
}

export const EditorTabs: React.FC<EditorTabsProps> = ({
  tabs,
  activeTabId,
  onSelectTab,
  onCloseTab,
}) => {
  if (tabs.length === 0) return null;

  return (
    <div className="editor-tabs-bar" role="tablist">
      {tabs.map((tab) => {
        const isActive = tab.id === activeTabId;
        return (
          <div
            key={tab.id}
            className={`editor-tab ${isActive ? 'active' : ''}`}
            onClick={() => onSelectTab(tab.id)}
            role="tab"
            aria-selected={isActive}
            title={tab.path}
          >
            <FileIcon name={tab.name} size={14} />
            <span style={{ maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {tab.name}
            </span>

            {tab.isDirty && (
              <span className="unsaved-dot" title="Unsaved changes" />
            )}

            <button
              type="button"
              className="tab-close-btn"
              onClick={(e) => onCloseTab(tab.id, e)}
              aria-label={`Close ${tab.name}`}
            >
              <X size={12} />
            </button>
          </div>
        );
      })}
    </div>
  );
};
