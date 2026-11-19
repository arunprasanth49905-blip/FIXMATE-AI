import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FolderGit2,
  Plus,
  Search,
  ArrowUpDown,
  Calendar,
  Edit2,
  Trash2,
  FolderOpen,
  FileCode,
} from 'lucide-react';
import { apiClient, parseErrorMessage } from '../services/apiClient';
import { Project } from '../types/api';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';

export const ProjectsPage: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'updated_at' | 'created_at' | 'name'>('updated_at');
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isRenameModalOpen, setIsRenameModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  // Form states
  const [projectName, setProjectName] = useState('');
  const [projectDesc, setProjectDesc] = useState('');
  const [projectLanguage, setProjectLanguage] = useState('python');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadProjects = async (search?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiClient.getProjects(search);
      setProjects(res.projects);
    } catch (err: unknown) {
      const msg = parseErrorMessage(err, 'Failed to fetch projects. Please try again.');
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadProjects(searchQuery);
  };

  const sortedProjects = useMemo(() => {
    return [...projects].sort((a, b) => {
      if (sortBy === 'name') {
        return a.name.localeCompare(b.name);
      }
      if (sortBy === 'created_at') {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [projects, sortBy]);

  // Open Create Modal
  const openCreateModal = () => {
    setProjectName('');
    setProjectDesc('');
    setProjectLanguage('python');
    setFormError(null);
    setIsCreateModalOpen(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim()) {
      setFormError('Project name is required');
      return;
    }
    setIsSubmitting(true);
    setFormError(null);
    try {
      const newProj = await apiClient.createProject({
        name: projectName.trim(),
        description: projectDesc.trim() || undefined,
        language: projectLanguage,
      });
      setIsCreateModalOpen(false);
      // Navigate straight into the new workspace
      navigate(`/projects/${newProj.id}`);
    } catch (err: unknown) {
      const msg = parseErrorMessage(err, 'Failed to create project. Please try again.');
      setFormError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Open Rename Modal
  const openRenameModal = (proj: Project, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedProject(proj);
    setProjectName(proj.name);
    setProjectDesc(proj.description || '');
    setFormError(null);
    setIsRenameModalOpen(true);
  };

  const handleRenameSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProject || !projectName.trim()) return;
    setIsSubmitting(true);
    setFormError(null);
    try {
      const updated = await apiClient.updateProject(selectedProject.id, {
        name: projectName.trim(),
        description: projectDesc.trim() || undefined,
      });
      setProjects((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
      setIsRenameModalOpen(false);
      setSelectedProject(null);
    } catch (err: unknown) {
      const msg = parseErrorMessage(err, 'Failed to update project. Please try again.');
      setFormError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Open Delete Modal
  const openDeleteModal = (proj: Project, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedProject(proj);
    setIsDeleteModalOpen(true);
  };

  const handleDeleteSubmit = async () => {
    if (!selectedProject) return;
    setIsSubmitting(true);
    try {
      await apiClient.deleteProject(selectedProject.id);
      setProjects((prev) => prev.filter((p) => p.id !== selectedProject.id));
      setIsDeleteModalOpen(false);
      setSelectedProject(null);
    } catch (err: unknown) {
      alert(parseErrorMessage(err, 'Failed to delete project. Please try again.'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
      <div className="projects-header">
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-navy-900)', marginBottom: '4px' }}>
            Projects Directory
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--color-navy-600)' }}>
            Manage source code repositories, explore project files, and launch code workspace sessions.
          </p>
        </div>

        <Button variant="primary" onClick={openCreateModal} data-testid="create-project-btn">
          <Plus size={16} />
          <span>New Project</span>
        </Button>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <form onSubmit={handleSearchSubmit} className="search-filter-bar">
          <div className="search-input-wrapper">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              className="form-input search-input"
              placeholder="Search projects by name or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Button variant="secondary" type="submit">
            Search
          </Button>
        </form>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '13px', color: 'var(--color-navy-500)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <ArrowUpDown size={14} /> Sort:
          </span>
          <select
            className="form-select"
            style={{ width: 'auto', padding: '6px 10px', fontSize: '13px' }}
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
          >
            <option value="updated_at">Last Modified</option>
            <option value="created_at">Date Created</option>
            <option value="name">Alphabetical</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div style={{ padding: '60px 0', textAlign: 'center', color: 'var(--color-navy-500)' }}>
          Loading projects...
        </div>
      ) : error ? (
        <div style={{ padding: '24px', backgroundColor: 'var(--color-red-subtle)', borderRadius: '8px', border: '1px solid var(--color-red-border)' }}>
          <div style={{ fontWeight: 600, color: 'var(--color-red-danger)', marginBottom: '4px' }}>Error Loading Projects</div>
          <div style={{ fontSize: '13px', color: 'var(--color-navy-700)' }}>{error}</div>
          <Button variant="secondary" size="sm" onClick={() => loadProjects()} style={{ marginTop: '12px' }}>
            Retry
          </Button>
        </div>
      ) : sortedProjects.length === 0 ? (
        <div
          style={{
            padding: '60px 24px',
            textAlign: 'center',
            backgroundColor: 'var(--color-surface)',
            border: '1px dashed var(--color-border)',
            borderRadius: '12px',
          }}
        >
          <FolderGit2 size={40} style={{ color: 'var(--color-navy-400)', margin: '0 auto 12px' }} />
          <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-navy-900)', marginBottom: '6px' }}>
            {searchQuery ? 'No Matching Projects Found' : 'No Projects Created Yet'}
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--color-navy-600)', maxWidth: '440px', margin: '0 auto 20px' }}>
            {searchQuery
              ? 'Try modifying your search query or clear the filter to view all projects.'
              : 'Create a new project workspace to upload source code files, inspect AST syntax, and edit code.'}
          </p>
          <Button variant="primary" onClick={openCreateModal}>
            <Plus size={16} />
            <span>Create First Project</span>
          </Button>
        </div>
      ) : (
        <div className="grid-3" style={{ marginTop: 0 }}>
          {sortedProjects.map((project) => (
            <div
              key={project.id}
              className="project-card"
              onClick={() => navigate(`/projects/${project.id}`)}
              style={{ cursor: 'pointer' }}
              data-testid={`project-card-${project.id}`}
            >
              <div>
                <div className="project-card-header">
                  <h3 className="project-name">{project.name}</h3>
                  <Badge variant={project.language === 'python' ? 'blue' : 'success'}>
                    {project.language.toUpperCase()}
                  </Badge>
                </div>

                <p className="project-desc">
                  {project.description || 'No description provided.'}
                </p>
              </div>

              <div>
                <div className="project-meta">
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <FileCode size={13} /> {project.file_count || 0} files
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Calendar size={13} /> {new Date(project.updated_at).toLocaleDateString()}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '12px', paddingTop: '8px' }}>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/projects/${project.id}`);
                    }}
                  >
                    <FolderOpen size={13} /> Open
                  </Button>

                  <div style={{ display: 'flex', gap: '6px' }}>
                    <button
                      type="button"
                      className="icon-btn"
                      title="Rename Project"
                      onClick={(e) => openRenameModal(project, e)}
                    >
                      <Edit2 size={14} />
                    </button>
                    <button
                      type="button"
                      className="icon-btn"
                      title="Delete Project"
                      style={{ color: 'var(--color-red-danger)' }}
                      onClick={(e) => openDeleteModal(project, e)}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create New Project"
      >
        <form onSubmit={handleCreateSubmit}>
          {formError && (
            <div style={{ padding: '10px 12px', backgroundColor: 'var(--color-red-subtle)', color: 'var(--color-red-danger)', borderRadius: '6px', fontSize: '13px', marginBottom: '14px' }}>
              {formError}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Project Name *</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. ecommerce-backend or my-python-app"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              autoFocus
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Primary Language</label>
            <select
              className="form-select"
              value={projectLanguage}
              onChange={(e) => setProjectLanguage(e.target.value)}
            >
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
              <option value="general">General / Multi-Language</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Description (Optional)</label>
            <textarea
              className="form-textarea"
              placeholder="Brief summary of the codebase and architecture..."
              value={projectDesc}
              onChange={(e) => setProjectDesc(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsCreateModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" isLoading={isSubmitting}>
              Create Project
            </Button>
          </div>
        </form>
      </Modal>

      {/* Rename Project Modal */}
      <Modal
        isOpen={isRenameModalOpen}
        onClose={() => setIsRenameModalOpen(false)}
        title="Edit Project Details"
      >
        <form onSubmit={handleRenameSubmit}>
          {formError && (
            <div style={{ padding: '10px 12px', backgroundColor: 'var(--color-red-subtle)', color: 'var(--color-red-danger)', borderRadius: '6px', fontSize: '13px', marginBottom: '14px' }}>
              {formError}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Project Name *</label>
            <input
              type="text"
              className="form-input"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="form-textarea"
              value={projectDesc}
              onChange={(e) => setProjectDesc(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsRenameModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" isLoading={isSubmitting}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Project Confirmation Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title="Delete Project"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <p style={{ fontSize: '13.5px', color: 'var(--color-navy-700)' }}>
            Are you sure you want to delete project <strong>{selectedProject?.name}</strong>?
          </p>
          <div style={{ padding: '12px', backgroundColor: 'var(--color-red-subtle)', border: '1px solid var(--color-red-border)', borderRadius: '6px', fontSize: '12.5px', color: 'var(--color-red-danger)' }}>
            Warning: All associated files and workspace directories will be permanently removed from disk. This action cannot be undone.
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsDeleteModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="outline-danger"
              isLoading={isSubmitting}
              onClick={handleDeleteSubmit}
              data-testid="confirm-delete-project-btn"
            >
              Delete Project
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
