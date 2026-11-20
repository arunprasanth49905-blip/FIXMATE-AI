import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Save,
  Plus,
  FolderPlus,
  Code2,
  AlertCircle,
  Sparkles,
  Bug,
} from 'lucide-react';
import { apiClient, parseErrorMessage } from '../services/apiClient';
import { Project, FileTreeItem, ProjectAnalysisResponse, DetectionRunResponse } from '../types/api';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { FileExplorer } from '../components/workspace/FileExplorer';
import { EditorTabs, OpenTab } from '../components/workspace/EditorTabs';
import { CodeEditor } from '../components/workspace/CodeEditor';
import { AnalysisPanel } from '../components/analysis/AnalysisPanel';
import { DetectionPanel } from '../components/detection/DetectionPanel';

export const WorkspacePage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();

  // Project data
  const [project, setProject] = useState<Project | null>(null);
  const [files, setFiles] = useState<FileTreeItem[]>([]);
  const [isLoadingProject, setIsLoadingProject] = useState(true);
  const [projectError, setProjectError] = useState<string | null>(null);

  // Tabs and editor state
  const [openTabs, setOpenTabs] = useState<OpenTab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const [tabContents, setTabContents] = useState<Record<string, string>>({});
  const [savedContents, setSavedContents] = useState<Record<string, string>>({});
  const [tabBinaryStatus, setTabBinaryStatus] = useState<Record<string, boolean>>({});
  const [isLoadingFile, setIsLoadingFile] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSavedTime, setLastSavedTime] = useState<string | null>(null);

  // Modals
  const [isCreateFileModalOpen, setIsCreateFileModalOpen] = useState(false);
  const [isCreateFolderModalOpen, setIsCreateFolderModalOpen] = useState(false);
  const [isRenameItemModalOpen, setIsRenameItemModalOpen] = useState(false);
  const [isDeleteItemModalOpen, setIsDeleteItemModalOpen] = useState(false);
  const [isRenameProjectModalOpen, setIsRenameProjectModalOpen] = useState(false);

  // Modal context items
  const [targetParentPath, setTargetParentPath] = useState('');
  const [newFileName, setNewFileName] = useState('');
  const [selectedItem, setSelectedItem] = useState<FileTreeItem | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);
  const [editProjectName, setEditProjectName] = useState('');

  // Phase 3: Structural Intelligence & Parsing State
  const [isAnalysisPanelOpen, setIsAnalysisPanelOpen] = useState(false);
  const [latestAnalysis, setLatestAnalysis] = useState<ProjectAnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [editorTargetPosition, setEditorTargetPosition] = useState<{ line: number; column?: number } | null>(null);

  // Phase 4: Deterministic Bug Detection State
  const [isDetectionPanelOpen, setIsDetectionPanelOpen] = useState(false);
  const [latestDetection, setLatestDetection] = useState<DetectionRunResponse | null>(null);
  const [isDetecting, setIsDetecting] = useState(false);

  const activeTab = openTabs.find((t) => t.id === activeTabId);
  const activeContent = activeTabId ? tabContents[activeTabId] ?? '' : '';
  const isCurrentFileDirty = activeTabId ? tabContents[activeTabId] !== savedContents[activeTabId] : false;

  // Load project and file tree
  const loadWorkspace = useCallback(async () => {
    if (!projectId) return;
    setIsLoadingProject(true);
    setProjectError(null);
    try {
      const [projData, filesData] = await Promise.all([
        apiClient.getProject(projectId),
        apiClient.getProjectFiles(projectId, true) as Promise<FileTreeItem[]>,
      ]);
      setProject(projData);
      setFiles(filesData);

      // Attempt to load latest analysis if available (silent fallback if not yet analyzed)
      if (typeof apiClient.getLatestAnalysis === 'function') {
        try {
          const latest = await apiClient.getLatestAnalysis(projectId);
          setLatestAnalysis(latest);
        } catch {
          // No previous analysis exists, default clean state
        }
      }

      // Attempt to load latest bug detection if available
      if (typeof apiClient.getLatestDetection === 'function') {
        try {
          const latestDet = await apiClient.getLatestDetection(projectId);
          setLatestDetection(latestDet);
        } catch {
          // No previous detection run, default clean state
        }
      }
    } catch (err: unknown) {
      const msg = parseErrorMessage(err, 'Failed to load workspace.');
      setProjectError(msg);
    } finally {
      setIsLoadingProject(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace]);

  // Open file in tabs
  const handleSelectFile = async (item: FileTreeItem) => {
    if (item.is_directory) return;

    // Check if tab is already open
    const existing = openTabs.find((t) => t.id === item.id);
    if (existing) {
      setActiveTabId(item.id);
      return;
    }

    // Load file content from backend
    setIsLoadingFile(true);
    setFileError(null);
    try {
      const res = await apiClient.getFileContent(projectId!, item.id);
      const content = res.content || '';

      const newTab: OpenTab = {
        id: item.id,
        path: item.path,
        name: item.name,
        isDirty: false,
      };

      setOpenTabs((prev) => [...prev, newTab]);
      setActiveTabId(item.id);
      setTabContents((prev) => ({ ...prev, [item.id]: content }));
      setSavedContents((prev) => ({ ...prev, [item.id]: content }));
      setTabBinaryStatus((prev) => ({ ...prev, [item.id]: res.is_binary }));
    } catch (err: unknown) {
      const msg = parseErrorMessage(err, 'Failed to read file content.');
      setFileError(msg);
    } finally {
      setIsLoadingFile(false);
    }
  };

  // Close tab
  const handleCloseTab = (tabId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const tabToClose = openTabs.find((t) => t.id === tabId);
    if (!tabToClose) return;

    // If dirty, ask confirmation
    if (tabContents[tabId] !== savedContents[tabId]) {
      const confirmClose = window.confirm(`File '${tabToClose.name}' has unsaved changes. Close anyway?`);
      if (!confirmClose) return;
    }

    const nextTabs = openTabs.filter((t) => t.id !== tabId);
    setOpenTabs(nextTabs);

    if (activeTabId === tabId) {
      if (nextTabs.length > 0) {
        setActiveTabId(nextTabs[nextTabs.length - 1].id);
      } else {
        setActiveTabId(null);
      }
    }

    // Clean up cache
    setTabContents((prev) => {
      const copy = { ...prev };
      delete copy[tabId];
      return copy;
    });
    setSavedContents((prev) => {
      const copy = { ...prev };
      delete copy[tabId];
      return copy;
    });
  };

  // Handle content edit in Monaco
  const handleEditorChange = (newVal: string) => {
    if (!activeTabId) return;

    setTabContents((prev) => ({ ...prev, [activeTabId]: newVal }));
    const isDirty = newVal !== savedContents[activeTabId];

    setOpenTabs((prev) =>
      prev.map((t) => (t.id === activeTabId ? { ...t, isDirty } : t))
    );
  };

  // Save active file
  const handleSaveActiveFile = useCallback(async () => {
    if (!projectId || !activeTabId || !isCurrentFileDirty) return;

    setIsSaving(true);
    try {
      const contentToSave = tabContents[activeTabId] ?? '';
      await apiClient.saveFileContent(projectId, activeTabId, contentToSave);

      setSavedContents((prev) => ({ ...prev, [activeTabId]: contentToSave }));
      setOpenTabs((prev) =>
        prev.map((t) => (t.id === activeTabId ? { ...t, isDirty: false } : t))
      );
      setLastSavedTime(new Date().toLocaleTimeString());

      // Refresh file tree to update file size and project timestamp
      const updatedFiles = await apiClient.getProjectFiles(projectId, true) as FileTreeItem[];
      setFiles(updatedFiles);
    } catch (err: unknown) {
      alert(parseErrorMessage(err, 'Failed to save file. Please try again.'));
    } finally {
      setIsSaving(false);
    }
  }, [projectId, activeTabId, isCurrentFileDirty, tabContents]);

  // Global Ctrl+S / Cmd+S handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSaveActiveFile();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSaveActiveFile]);

  // Create file modal trigger
  const handleOpenCreateFile = (parentPath = '') => {
    setTargetParentPath(parentPath);
    setNewFileName('');
    setModalError(null);
    setIsCreateFileModalOpen(true);
  };

  const handleCreateFileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFileName.trim()) {
      setModalError('File name is required');
      return;
    }
    const cleanName = newFileName.trim();
    const fullPath = targetParentPath ? `${targetParentPath}/${cleanName}` : cleanName;

    try {
      const created = await apiClient.createProjectFile(projectId!, {
        path: fullPath,
        content: '',
        is_directory: false,
      });

      setIsCreateFileModalOpen(false);
      // Reload file tree
      const updatedFiles = await apiClient.getProjectFiles(projectId!, true) as FileTreeItem[];
      setFiles(updatedFiles);

      // Open newly created file in editor
      handleSelectFile({
        id: created.id,
        path: created.path,
        name: created.name,
        is_directory: false,
        size: created.size,
        extension: created.extension,
      });
    } catch (err: unknown) {
      setModalError(parseErrorMessage(err, 'File creation failed. Please try again.'));
    }
  };

  // Create folder modal trigger
  const handleOpenCreateFolder = (parentPath = '') => {
    setTargetParentPath(parentPath);
    setNewFileName('');
    setModalError(null);
    setIsCreateFolderModalOpen(true);
  };

  const handleCreateFolderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFileName.trim()) {
      setModalError('Folder name is required');
      return;
    }
    const cleanName = newFileName.trim();
    const fullPath = targetParentPath ? `${targetParentPath}/${cleanName}` : cleanName;

    try {
      await apiClient.createProjectFile(projectId!, {
        path: fullPath,
        is_directory: true,
      });
      setIsCreateFolderModalOpen(false);
      const updatedFiles = await apiClient.getProjectFiles(projectId!, true) as FileTreeItem[];
      setFiles(updatedFiles);
    } catch (err: unknown) {
      setModalError(parseErrorMessage(err, 'Folder creation failed. Please try again.'));
    }
  };

  // Rename item
  const handleOpenRenameItem = (item: FileTreeItem) => {
    setSelectedItem(item);
    setNewFileName(item.name);
    setModalError(null);
    setIsRenameItemModalOpen(true);
  };

  const handleRenameItemSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem || !newFileName.trim()) return;

    const parts = selectedItem.path.split('/');
    parts[parts.length - 1] = newFileName.trim();
    const newPath = parts.join('/');

    try {
      const updated = await apiClient.renameFile(projectId!, selectedItem.id, newPath);
      setIsRenameItemModalOpen(false);

      // Update open tabs if renamed
      setOpenTabs((prev) =>
        prev.map((t) =>
          t.id === selectedItem.id ? { ...t, name: updated.name, path: updated.path } : t
        )
      );

      const updatedFiles = await apiClient.getProjectFiles(projectId!, true) as FileTreeItem[];
      setFiles(updatedFiles);
    } catch (err: unknown) {
      setModalError(parseErrorMessage(err, 'Failed to rename item. Please try again.'));
    }
  };

  // Delete item
  const handleOpenDeleteItem = (item: FileTreeItem) => {
    setSelectedItem(item);
    setIsDeleteItemModalOpen(true);
  };

  const handleDeleteItemSubmit = async () => {
    if (!selectedItem) return;
    try {
      await apiClient.deleteFile(projectId!, selectedItem.id);
      setIsDeleteItemModalOpen(false);

      // Close tab if open
      setOpenTabs((prev) => prev.filter((t) => t.id !== selectedItem.id));
      if (activeTabId === selectedItem.id) {
        setActiveTabId(null);
      }

      const updatedFiles = await apiClient.getProjectFiles(projectId!, true) as FileTreeItem[];
      setFiles(updatedFiles);
    } catch (err: unknown) {
      alert(parseErrorMessage(err, 'Failed to delete item. Please try again.'));
    }
  };

  // Upload files handler
  const handleUploadFiles = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;

    const formData = new FormData();
    for (let i = 0; i < fileList.length; i++) {
      formData.append('files', fileList[i]);
    }

    try {
      const res = await apiClient.uploadFiles(projectId!, formData);
      if (res.errors && res.errors.length > 0) {
        alert(`Some files failed to upload:\n${res.errors.join('\n')}`);
      }
      const updatedFiles = await apiClient.getProjectFiles(projectId!, true) as FileTreeItem[];
      setFiles(updatedFiles);
    } catch (err: unknown) {
      alert(parseErrorMessage(err, 'Upload failed. Please try again.'));
    } finally {
      e.target.value = '';
    }
  };

  // Rename project
  const handleRenameProjectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editProjectName.trim() || !project) return;
    try {
      const updated = await apiClient.updateProject(project.id, { name: editProjectName.trim() });
      setProject(updated);
      setIsRenameProjectModalOpen(false);
    } catch (err: unknown) {
      setModalError(parseErrorMessage(err, 'Failed to rename project. Please try again.'));
    }
  };

  // Phase 3: Trigger Codebase Parsing
  const handleTriggerAnalysis = async () => {
    if (!projectId) return;
    setIsAnalyzing(true);
    try {
      const res = await apiClient.analyzeProject(projectId);
      setLatestAnalysis(res);
      setIsAnalysisPanelOpen(true);
      setIsDetectionPanelOpen(false);
    } catch (err: unknown) {
      const msg = parseErrorMessage(err, 'Codebase analysis failed. Please check logs.');
      alert(msg);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Phase 4: Trigger Deterministic Bug Detection
  const handleTriggerDetection = async () => {
    if (!projectId) return;
    setIsDetecting(true);
    try {
      const res = await apiClient.runBugDetection(projectId);
      setLatestDetection(res);
      setIsDetectionPanelOpen(true);
      setIsAnalysisPanelOpen(false);
    } catch (err: unknown) {
      const msg = parseErrorMessage(err, 'Bug detection failed. Please check logs.');
      alert(msg);
    } finally {
      setIsDetecting(false);
    }
  };

  // Phase 3: Navigate from Symbol/Diagnostic to Monaco Editor
  const handleNavigateToSource = (targetPath: string, line: number, column = 0) => {
    const findItemInTree = (items: FileTreeItem[]): FileTreeItem | null => {
      for (const item of items) {
        if (item.path === targetPath || item.path.endsWith(targetPath)) return item;
        if (item.children) {
          const found = findItemInTree(item.children);
          if (found) return found;
        }
      }
      return null;
    };

    const targetFile = findItemInTree(files);
    if (targetFile) {
      handleSelectFile(targetFile);
    }

    setEditorTargetPosition({ line, column });
  };

  // Phase 7: Reload workspace files and active editor content when a patch is applied or rolled back
  const handleFileModified = async (filePath: string) => {
    try {
      const updatedFiles = await apiClient.getProjectFiles(projectId!, true) as FileTreeItem[];
      setFiles(updatedFiles);

      if (activeTab && (activeTab.path === filePath || activeTab.path.endsWith(filePath))) {
        const fileRes = await apiClient.getFileContent(projectId!, activeTab.id);
        const safeContent = fileRes.content ?? '';
        setTabContents((prev) => ({ ...prev, [activeTab.id]: safeContent }));
        setSavedContents((prev) => ({ ...prev, [activeTab.id]: safeContent }));
        setOpenTabs((prev) =>
          prev.map((t) => (t.id === activeTab.id ? { ...t, isDirty: false } : t))
        );
      }
    } catch {
      // Best-effort background refresh
    }
  };

  if (isLoadingProject) {
    return (
      <div style={{ padding: '60px', textAlign: 'center', color: 'var(--color-navy-500)' }}>
        Loading project workspace...
      </div>
    );
  }

  if (projectError || !project) {
    return (
      <div style={{ maxWidth: '600px', margin: '40px auto', padding: '24px', backgroundColor: 'var(--color-red-subtle)', borderRadius: '8px', border: '1px solid var(--color-red-border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-red-danger)', fontWeight: 600, marginBottom: '6px' }}>
          <AlertCircle size={18} />
          <span>Project Not Found</span>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--color-navy-700)', marginBottom: '16px' }}>
          {projectError || 'The requested project workspace does not exist or has been removed.'}
        </p>
        <Link to="/projects" className="btn btn-secondary btn-sm">
          <ArrowLeft size={13} /> Return to Projects
        </Link>
      </div>
    );
  }

  return (
    <div className="workspace-container">
      {/* Top Workspace Toolbar */}
      <header className="workspace-toolbar">
        <div className="workspace-toolbar-left">
          <Link
            to="/projects"
            className="btn btn-secondary btn-sm"
            style={{ padding: '4px 8px', fontSize: '12px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
            title="Back to Projects"
          >
            <ArrowLeft size={13} />
            <span>Projects</span>
          </Link>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{ fontWeight: 700, fontSize: '14.5px', color: 'var(--color-navy-900)', cursor: 'pointer' }}
              title="Click to rename project"
              onClick={() => {
                setEditProjectName(project.name);
                setModalError(null);
                setIsRenameProjectModalOpen(true);
              }}
            >
              {project.name}
            </span>
            <Badge variant="blue">{project.language.toUpperCase()}</Badge>
          </div>
        </div>

        <div className="workspace-toolbar-right">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setIsAnalysisPanelOpen(!isAnalysisPanelOpen);
              if (!isAnalysisPanelOpen) setIsDetectionPanelOpen(false);
            }}
            data-testid="toggle-intelligence-button"
            title="Toggle Structural Code Intelligence (Phase 3)"
            style={{
              borderColor: isAnalysisPanelOpen ? 'var(--color-blue-primary)' : undefined,
              backgroundColor: isAnalysisPanelOpen ? 'var(--color-blue-subtle)' : undefined,
            }}
          >
            <Sparkles size={13} style={{ color: 'var(--color-blue-primary)' }} />
            <span>Intelligence</span>
            {latestAnalysis && (
              <span
                style={{
                  fontSize: '11px',
                  padding: '1px 5px',
                  borderRadius: '10px',
                  backgroundColor: latestAnalysis.total_diagnostics_count > 0 ? 'var(--color-amber-subtle)' : 'var(--color-surface)',
                  color: latestAnalysis.total_diagnostics_count > 0 ? 'var(--color-amber-warning)' : 'var(--color-navy-600)',
                  fontWeight: 600,
                  marginLeft: '2px',
                }}
              >
                {latestAnalysis.statistics.parsed_files}
              </span>
            )}
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setIsDetectionPanelOpen(!isDetectionPanelOpen);
              if (!isDetectionPanelOpen) setIsAnalysisPanelOpen(false);
            }}
            data-testid="toggle-detection-button"
            title="Toggle Deterministic Bug Detection (Phase 4)"
            style={{
              borderColor: isDetectionPanelOpen ? 'var(--color-red-danger)' : undefined,
              backgroundColor: isDetectionPanelOpen ? 'var(--color-red-subtle)' : undefined,
            }}
          >
            <Bug size={13} style={{ color: 'var(--color-red-danger)' }} />
            <span>Bug Detection</span>
            {latestDetection && (
              <span
                style={{
                  fontSize: '11px',
                  padding: '1px 5px',
                  borderRadius: '10px',
                  backgroundColor: latestDetection.total_findings > 0 ? 'var(--color-red-subtle)' : 'var(--color-surface)',
                  color: latestDetection.total_findings > 0 ? 'var(--color-red-danger)' : 'var(--color-navy-600)',
                  fontWeight: 600,
                  marginLeft: '2px',
                }}
              >
                {latestDetection.total_findings}
              </span>
            )}
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleOpenCreateFile()}
            title="Create File"
          >
            <Plus size={13} /> File
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleOpenCreateFolder()}
            title="Create Folder"
          >
            <FolderPlus size={13} /> Folder
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleSaveActiveFile}
            disabled={!activeTabId || !isCurrentFileDirty || isSaving}
            isLoading={isSaving}
            data-testid="save-file-button"
            title="Save file (Ctrl+S)"
          >
            <Save size={13} />
            <span>{isSaving ? 'Saving...' : 'Save'}</span>
          </Button>
        </div>
      </header>

      {/* Main Workspace Area */}
      <div className="workspace-main">
        {/* Left: File Explorer */}
        <FileExplorer
          files={files}
          activeFileId={activeTabId}
          onSelectFile={handleSelectFile}
          onCreateFile={handleOpenCreateFile}
          onCreateFolder={handleOpenCreateFolder}
          onRenameItem={handleOpenRenameItem}
          onDeleteItem={handleOpenDeleteItem}
          onUploadFiles={handleUploadFiles}
        />

        {/* Right: Code Editor Pane */}
        <main className="editor-pane" style={{ flex: (isAnalysisPanelOpen || isDetectionPanelOpen) ? '1 1 50%' : '1' }}>
          <EditorTabs
            tabs={openTabs}
            activeTabId={activeTabId}
            onSelectTab={(id) => setActiveTabId(id)}
            onCloseTab={handleCloseTab}
          />

          {activeTab ? (
            <CodeEditor
              value={activeContent}
              onChange={handleEditorChange}
              fileName={activeTab.name}
              isBinary={tabBinaryStatus[activeTab.id] || false}
              isLoading={isLoadingFile}
              error={fileError}
              targetPosition={editorTargetPosition}
            />
          ) : (
            <div className="editor-empty-state">
              <Code2 size={48} style={{ color: 'var(--color-navy-300)', marginBottom: '14px' }} />
              <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-navy-800)', marginBottom: '6px' }}>
                No File Open
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--color-navy-500)', maxWidth: '400px', lineHeight: 1.5, marginBottom: '20px' }}>
                Select a source file from the explorer on the left or create a new file to start viewing and editing.
              </p>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleOpenCreateFile()}
              >
                <Plus size={13} /> Create New File
              </Button>
            </div>
          )}

          {/* Bottom Editor Status Bar */}
          <footer className="editor-status-bar">
            <div>
              {activeTab ? (
                <span>
                  {activeTab.path} {isCurrentFileDirty ? '(Modified)' : ''}
                </span>
              ) : (
                <span>Workspace Ready</span>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              {activeTab && (
                <>
                  <span>{activeContent.length} chars</span>
                  <span>UTF-8</span>
                  <span style={{ color: isCurrentFileDirty ? 'var(--color-amber-warning)' : 'var(--color-green-success)', fontWeight: 600 }}>
                    {isCurrentFileDirty ? '● Unsaved' : '✓ Saved'}
                  </span>
                </>
              )}
              {lastSavedTime && !isCurrentFileDirty && (
                <span>Last saved at {lastSavedTime}</span>
              )}
            </div>
          </footer>
        </main>

        {/* Phase 3 Code Intelligence Side Panel */}
        {isAnalysisPanelOpen && (
          <aside
            style={{
              flex: '1 1 50%',
              maxWidth: '680px',
              minWidth: '380px',
              height: '100%',
              zIndex: 5,
            }}
          >
            <AnalysisPanel
              projectId={projectId!}
              analysis={latestAnalysis}
              isAnalyzing={isAnalyzing}
              onAnalyzeProject={handleTriggerAnalysis}
              onClose={() => setIsAnalysisPanelOpen(false)}
              onNavigateToSource={handleNavigateToSource}
            />
          </aside>
        )}

        {/* Phase 4 Deterministic Bug Detection Side Panel */}
        {isDetectionPanelOpen && (
          <aside
            style={{
              flex: '1 1 50%',
              maxWidth: '680px',
              minWidth: '380px',
              height: '100%',
              zIndex: 5,
            }}
          >
            <DetectionPanel
              projectId={projectId!}
              detection={latestDetection}
              isDetecting={isDetecting}
              onRunDetection={handleTriggerDetection}
              onClose={() => setIsDetectionPanelOpen(false)}
              onNavigateToSource={handleNavigateToSource}
              onFileModified={handleFileModified}
            />
          </aside>
        )}
      </div>

      {/* Modal: Create File */}
      <Modal
        isOpen={isCreateFileModalOpen}
        onClose={() => setIsCreateFileModalOpen(false)}
        title="Create New File"
      >
        <form onSubmit={handleCreateFileSubmit}>
          {modalError && (
            <div data-testid="modal-error" style={{ padding: '8px 12px', backgroundColor: 'var(--color-red-subtle)', color: 'var(--color-red-danger)', borderRadius: '6px', fontSize: '12.5px', marginBottom: '12px' }}>
              {modalError}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">
              File Name {targetParentPath ? `(inside ${targetParentPath}/)` : ''}
            </label>
            <input
              type="text"
              data-testid="file-path-input"
              className="form-input"
              placeholder="e.g. main.py or server.js"
              value={newFileName}
              onChange={(e) => setNewFileName(e.target.value)}
              autoFocus
              required
            />
            <span style={{ fontSize: '11.5px', color: 'var(--color-navy-400)', marginTop: '4px' }}>
              Supported: .py, .js, .ts, .json, .md, .txt, .css, .html, etc.
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
            <Button type="button" variant="secondary" onClick={() => setIsCreateFileModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" data-testid="create-file-submit">
              Create File
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Create Folder */}
      <Modal
        isOpen={isCreateFolderModalOpen}
        onClose={() => setIsCreateFolderModalOpen(false)}
        title="Create New Folder"
      >
        <form onSubmit={handleCreateFolderSubmit}>
          {modalError && (
            <div style={{ padding: '8px 12px', backgroundColor: 'var(--color-red-subtle)', color: 'var(--color-red-danger)', borderRadius: '6px', fontSize: '12.5px', marginBottom: '12px' }}>
              {modalError}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">
              Folder Name {targetParentPath ? `(inside ${targetParentPath}/)` : ''}
            </label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. src or utils"
              value={newFileName}
              onChange={(e) => setNewFileName(e.target.value)}
              autoFocus
              required
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
            <Button type="button" variant="secondary" onClick={() => setIsCreateFolderModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Create Folder
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Rename Item */}
      <Modal
        isOpen={isRenameItemModalOpen}
        onClose={() => setIsRenameItemModalOpen(false)}
        title={`Rename ${selectedItem?.is_directory ? 'Folder' : 'File'}`}
      >
        <form onSubmit={handleRenameItemSubmit}>
          {modalError && (
            <div style={{ padding: '8px 12px', backgroundColor: 'var(--color-red-subtle)', color: 'var(--color-red-danger)', borderRadius: '6px', fontSize: '12.5px', marginBottom: '12px' }}>
              {modalError}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">New Name</label>
            <input
              type="text"
              className="form-input"
              value={newFileName}
              onChange={(e) => setNewFileName(e.target.value)}
              autoFocus
              required
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
            <Button type="button" variant="secondary" onClick={() => setIsRenameItemModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Rename
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Delete Item Confirmation */}
      <Modal
        isOpen={isDeleteItemModalOpen}
        onClose={() => setIsDeleteItemModalOpen(false)}
        title={`Delete ${selectedItem?.is_directory ? 'Folder' : 'File'}`}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <p style={{ fontSize: '13.5px', color: 'var(--color-navy-700)' }}>
            Are you sure you want to delete <strong>{selectedItem?.path}</strong>?
          </p>
          {selectedItem?.is_directory && (
            <div style={{ padding: '10px 12px', backgroundColor: 'var(--color-red-subtle)', color: 'var(--color-red-danger)', borderRadius: '6px', fontSize: '12px' }}>
              Warning: All files inside this folder will also be permanently deleted.
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
            <Button type="button" variant="secondary" onClick={() => setIsDeleteItemModalOpen(false)}>
              Cancel
            </Button>
            <Button type="button" variant="outline-danger" onClick={handleDeleteItemSubmit}>
              Delete Permanently
            </Button>
          </div>
        </div>
      </Modal>

      {/* Modal: Rename Project */}
      <Modal
        isOpen={isRenameProjectModalOpen}
        onClose={() => setIsRenameProjectModalOpen(false)}
        title="Rename Project"
      >
        <form onSubmit={handleRenameProjectSubmit}>
          {modalError && (
            <div style={{ padding: '8px 12px', backgroundColor: 'var(--color-red-subtle)', color: 'var(--color-red-danger)', borderRadius: '6px', fontSize: '12.5px', marginBottom: '12px' }}>
              {modalError}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Project Name</label>
            <input
              type="text"
              className="form-input"
              value={editProjectName}
              onChange={(e) => setEditProjectName(e.target.value)}
              autoFocus
              required
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
            <Button type="button" variant="secondary" onClick={() => setIsRenameProjectModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Save
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
