import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  RefreshCw,
  Search,
  Filter,
  FolderGit2,
  FileCode,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  Layers,
  ArrowRight,
  Clock,
  AlertOctagon,
} from 'lucide-react';
import { apiClient, parseErrorMessage } from '../services/apiClient';
import {
  VerificationListItem,
  VerificationOverviewMetrics,
  Project,
} from '../types/api';
import { RepairVerificationCard } from '../components/repair/RepairVerificationCard';
import { Modal } from '../components/common/Modal';

export const TestResultsPage: React.FC = () => {
  const navigate = useNavigate();

  // Data states
  const [items, setItems] = useState<VerificationListItem[]>([]);
  const [metrics, setMetrics] = useState<VerificationOverviewMetrics>({
    total_attempts: 0,
    verified_count: 0,
    failed_count: 0,
    partial_count: 0,
    inconclusive_count: 0,
    stale_count: 0,
  });
  const [projects, setProjects] = useState<Project[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);

  // Filter states
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 15;

  // UI state
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<VerificationListItem | null>(null);

  // Load projects list for project dropdown
  useEffect(() => {
    apiClient
      .getProjects()
      .then((res) => {
        setProjects(res.projects || []);
      })
      .catch((err) => {
        console.warn('Failed to fetch projects list for filter:', err);
      });
  }, []);

  // Fetch verification results from real API
  const loadVerifications = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiClient.getVerificationHistoryList({
        projectId: selectedProjectId || undefined,
        status: selectedStatus || undefined,
        search: searchQuery.trim() || undefined,
        page: currentPage,
        pageSize,
      });

      setItems(res.items || []);
      setMetrics(res.metrics);
      setTotalCount(res.total);
      setTotalPages(res.total_pages);
    } catch (err: unknown) {
      const msg = parseErrorMessage(err, 'Failed to fetch verification records.');
      setError(msg);
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  }, [selectedProjectId, selectedStatus, searchQuery, currentPage]);

  useEffect(() => {
    loadVerifications();
  }, [loadVerifications]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    loadVerifications();
  };

  const handleClearFilters = () => {
    setSelectedProjectId('');
    setSelectedStatus('');
    setSearchQuery('');
    setCurrentPage(1);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'verified':
        return (
          <span
            data-testid="status-badge-verified"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 700,
              backgroundColor: '#ecfdf5',
              color: '#065f46',
              border: '1px solid #10b981',
              textTransform: 'uppercase',
            }}
          >
            <CheckCircle2 size={12} style={{ color: '#10b981' }} />
            VERIFIED
          </span>
        );
      case 'failed':
        return (
          <span
            data-testid="status-badge-failed"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 700,
              backgroundColor: '#fef2f2',
              color: '#991b1b',
              border: '1px solid #ef4444',
              textTransform: 'uppercase',
            }}
          >
            <XCircle size={12} style={{ color: '#ef4444' }} />
            FAILED
          </span>
        );
      case 'partial':
        return (
          <span
            data-testid="status-badge-partial"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 700,
              backgroundColor: '#fefce8',
              color: '#854d0e',
              border: '1px solid #eab308',
              textTransform: 'uppercase',
            }}
          >
            <AlertTriangle size={12} style={{ color: '#eab308' }} />
            PARTIAL
          </span>
        );
      case 'stale':
        return (
          <span
            data-testid="status-badge-stale"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 700,
              backgroundColor: '#fffbeb',
              color: '#92400e',
              border: '1px solid #f59e0b',
              textTransform: 'uppercase',
            }}
          >
            <AlertTriangle size={12} style={{ color: '#f59e0b' }} />
            STALE
          </span>
        );
      default:
        return (
          <span
            data-testid="status-badge-inconclusive"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '3px 8px',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 700,
              backgroundColor: '#f5f3ff',
              color: '#5b21b6',
              border: '1px solid #8b5cf6',
              textTransform: 'uppercase',
            }}
          >
            <HelpCircle size={12} style={{ color: '#8b5cf6' }} />
            {status.toUpperCase()}
          </span>
        );
    }
  };

  const hasActiveFilters = Boolean(selectedProjectId || selectedStatus || searchQuery);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* =========================================================================
          1. HEADER SECTION
         ========================================================================= */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          paddingBottom: '16px',
          borderBottom: '1px solid var(--color-border, #e2e8f0)',
        }}
      >
        <div>
          <h1
            style={{
              margin: 0,
              fontSize: '22px',
              fontWeight: 700,
              color: 'var(--color-navy-900, #0f172a)',
              letterSpacing: '-0.02em',
            }}
          >
            Test Results & Verification Reports
          </h1>
          <div style={{ fontSize: '13px', color: 'var(--color-navy-500, #64748b)', marginTop: '4px' }}>
            Automated static validation records evaluating syntax validity, target bug resolution, and regression analysis.
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => loadVerifications()}
            disabled={isLoading}
            data-testid="refresh-verifications-btn"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              backgroundColor: '#ffffff',
              color: 'var(--color-navy-700, #334155)',
              border: '1px solid var(--color-border, #cbd5e1)',
              borderRadius: '6px',
              fontSize: '12.5px',
              fontWeight: 600,
              cursor: isLoading ? 'not-allowed' : 'pointer',
              boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
            }}
            title="Refresh verification results"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            <span>{isLoading ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* =========================================================================
          2. OVERVIEW METRICS CARDS (Real DB Values)
         ========================================================================= */}
      <div
        data-testid="verification-metrics-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: '12px',
        }}
      >
        {/* Total Verification Attempts */}
        <div
          style={{
            padding: '14px 16px',
            backgroundColor: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#64748b' }}>Total Attempts</span>
            <Layers size={16} style={{ color: '#3b82f6' }} />
          </div>
          <div
            data-testid="metric-total-attempts"
            style={{ fontSize: '24px', fontWeight: 800, color: '#1e293b', marginTop: '6px' }}
          >
            {metrics.total_attempts}
          </div>
        </div>

        {/* Verified Repairs */}
        <div
          style={{
            padding: '14px 16px',
            backgroundColor: '#f0fdf4',
            border: '1px solid #bbf7d0',
            borderRadius: '8px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#166534' }}>Verified Repairs</span>
            <CheckCircle2 size={16} style={{ color: '#16a34a' }} />
          </div>
          <div
            data-testid="metric-verified-count"
            style={{ fontSize: '24px', fontWeight: 800, color: '#14532d', marginTop: '6px' }}
          >
            {metrics.verified_count}
          </div>
        </div>

        {/* Failed Verifications */}
        <div
          style={{
            padding: '14px 16px',
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '8px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#991b1b' }}>Failed</span>
            <XCircle size={16} style={{ color: '#dc2626' }} />
          </div>
          <div
            data-testid="metric-failed-count"
            style={{ fontSize: '24px', fontWeight: 800, color: '#7f1d1d', marginTop: '6px' }}
          >
            {metrics.failed_count}
          </div>
        </div>

        {/* Partial Verifications */}
        <div
          style={{
            padding: '14px 16px',
            backgroundColor: '#fefce8',
            border: '1px solid #fef08a',
            borderRadius: '8px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#854d0e' }}>Partial</span>
            <AlertTriangle size={16} style={{ color: '#ca8a04' }} />
          </div>
          <div
            data-testid="metric-partial-count"
            style={{ fontSize: '24px', fontWeight: 800, color: '#713f12', marginTop: '6px' }}
          >
            {metrics.partial_count}
          </div>
        </div>

        {/* Inconclusive Verifications */}
        <div
          style={{
            padding: '14px 16px',
            backgroundColor: '#f5f3ff',
            border: '1px solid #ddd6fe',
            borderRadius: '8px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#5b21b6' }}>Inconclusive</span>
            <HelpCircle size={16} style={{ color: '#7c3aed' }} />
          </div>
          <div
            data-testid="metric-inconclusive-count"
            style={{ fontSize: '24px', fontWeight: 800, color: '#4c1d95', marginTop: '6px' }}
          >
            {metrics.inconclusive_count}
          </div>
        </div>

        {/* Stale Verifications */}
        <div
          style={{
            padding: '14px 16px',
            backgroundColor: '#fffbeb',
            border: '1px solid #fde68a',
            borderRadius: '8px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#92400e' }}>Stale</span>
            <Clock size={16} style={{ color: '#d97706' }} />
          </div>
          <div
            data-testid="metric-stale-count"
            style={{ fontSize: '24px', fontWeight: 800, color: '#78350f', marginTop: '6px' }}
          >
            {metrics.stale_count}
          </div>
        </div>
      </div>

      {/* =========================================================================
          3. FILTER & SEARCH CONTROLS
         ========================================================================= */}
      <div
        style={{
          padding: '12px 16px',
          backgroundColor: '#ffffff',
          border: '1px solid var(--color-border, #e2e8f0)',
          borderRadius: '8px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
        }}
      >
        <form
          onSubmit={handleSearchSubmit}
          style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: '1 1 300px' }}
        >
          <div style={{ position: 'relative', width: '100%', maxWidth: '360px' }}>
            <Search
              size={15}
              style={{
                position: 'absolute',
                left: '10px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#94a3b8',
              }}
            />
            <input
              type="text"
              placeholder="Search file path, rule ID, or project..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              data-testid="verification-search-input"
              style={{
                width: '100%',
                padding: '7px 10px 7px 32px',
                fontSize: '12.5px',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                outline: 'none',
              }}
            />
          </div>
          <button
            type="submit"
            style={{
              padding: '7px 12px',
              backgroundColor: '#0284c7',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Search
          </button>
        </form>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {/* Project Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <FolderGit2 size={14} style={{ color: '#64748b' }} />
            <select
              value={selectedProjectId}
              onChange={(e) => {
                setSelectedProjectId(e.target.value);
                setCurrentPage(1);
              }}
              data-testid="project-filter-select"
              style={{
                padding: '6px 10px',
                fontSize: '12px',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                backgroundColor: '#ffffff',
                color: '#1e293b',
              }}
            >
              <option value="">All Projects</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Filter size={14} style={{ color: '#64748b' }} />
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setCurrentPage(1);
              }}
              data-testid="status-filter-select"
              style={{
                padding: '6px 10px',
                fontSize: '12px',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                backgroundColor: '#ffffff',
                color: '#1e293b',
              }}
            >
              <option value="">All Statuses</option>
              <option value="verified">Verified</option>
              <option value="failed">Failed</option>
              <option value="partial">Partial</option>
              <option value="stale">Stale</option>
              <option value="inconclusive">Inconclusive</option>
            </select>
          </div>

          {hasActiveFilters && (
            <button
              onClick={handleClearFilters}
              data-testid="clear-filters-btn"
              style={{
                padding: '6px 10px',
                fontSize: '11.5px',
                color: '#64748b',
                background: 'none',
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* =========================================================================
          4. ERROR STATE
         ========================================================================= */}
      {error && (
        <div
          data-testid="test-results-error-banner"
          style={{
            padding: '12px 16px',
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '8px',
            color: '#991b1b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
            <AlertOctagon size={16} style={{ color: '#dc2626' }} />
            <span>{error}</span>
          </div>
          <button
            onClick={() => loadVerifications()}
            style={{
              padding: '5px 10px',
              backgroundColor: '#dc2626',
              color: '#ffffff',
              border: 'none',
              borderRadius: '4px',
              fontSize: '11.5px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* =========================================================================
          5. MAIN CONTENT AREA (Loading / Empty / Table)
         ========================================================================= */}
      {isLoading ? (
        <div
          data-testid="test-results-loading"
          style={{
            padding: '60px 20px',
            textAlign: 'center',
            backgroundColor: '#ffffff',
            borderRadius: '8px',
            border: '1px solid #e2e8f0',
          }}
        >
          <RefreshCw size={24} className="animate-spin" style={{ color: '#0284c7', margin: '0 auto 12px' }} />
          <div style={{ fontSize: '14px', fontWeight: 600, color: '#334155' }}>
            Loading verification records...
          </div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
            Reading persisted static verification results from the database.
          </div>
        </div>
      ) : items.length === 0 ? (
        /* Empty States */
        <div
          data-testid="test-results-empty-state"
          style={{
            padding: '50px 20px',
            textAlign: 'center',
            backgroundColor: '#ffffff',
            borderRadius: '8px',
            border: '1px solid #e2e8f0',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '24px',
              backgroundColor: '#f0fdf4',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <ShieldCheck size={26} style={{ color: '#16a34a' }} />
          </div>

          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: '#1e293b' }}>
            {hasActiveFilters ? 'No Matching Verification Records' : 'No Verification Records Yet'}
          </h3>

          <p style={{ margin: 0, fontSize: '13px', color: '#64748b', maxWidth: '480px', lineHeight: 1.5 }}>
            {hasActiveFilters
              ? 'No verification records match your selected project, status, or search filters. Try clearing filters to see all runs.'
              : 'Automated verification records are created in Phase 8 after an approved code repair is applied to disk and verified. Run bug detection, synthesize a repair, approve and apply it, then run verification to see results here.'}
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '8px' }}>
            {hasActiveFilters ? (
              <button
                onClick={handleClearFilters}
                style={{
                  padding: '7px 14px',
                  backgroundColor: '#0284c7',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '12.5px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Reset Filters
              </button>
            ) : (
              <>
                <button
                  onClick={() => navigate('/projects')}
                  data-testid="go-to-projects-btn"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '8px 14px',
                    backgroundColor: '#0284c7',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '12.5px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <FolderGit2 size={14} />
                  <span>Go to Projects</span>
                </button>

                <button
                  onClick={() => navigate('/analysis')}
                  data-testid="new-analysis-btn"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '8px 14px',
                    backgroundColor: '#ffffff',
                    color: '#334155',
                    border: '1px solid #cbd5e1',
                    borderRadius: '6px',
                    fontSize: '12.5px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <span>New Analysis</span>
                  <ArrowRight size={14} />
                </button>
              </>
            )}
          </div>
        </div>
      ) : (
        /* Results Table */
        <div
          data-testid="test-results-table-container"
          style={{
            backgroundColor: '#ffffff',
            borderRadius: '8px',
            border: '1px solid #e2e8f0',
            overflow: 'hidden',
            boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
          }}
        >
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12.5px' }}>
            <thead>
              <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#64748b', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                <th style={{ padding: '10px 14px', fontWeight: 700 }}>Status</th>
                <th style={{ padding: '10px 14px', fontWeight: 700 }}>Verification ID</th>
                <th style={{ padding: '10px 14px', fontWeight: 700 }}>Project</th>
                <th style={{ padding: '10px 14px', fontWeight: 700 }}>Target File</th>
                <th style={{ padding: '10px 14px', fontWeight: 700 }}>Target Bug</th>
                <th style={{ padding: '10px 14px', fontWeight: 700 }}>Regressions</th>
                <th style={{ padding: '10px 14px', fontWeight: 700 }}>Duration</th>
                <th style={{ padding: '10px 14px', fontWeight: 700 }}>Verified At</th>
                <th style={{ padding: '10px 14px', fontWeight: 700, textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => (
                <tr
                  key={item.id}
                  data-testid={`verification-row-${item.id}`}
                  onClick={() => setSelectedReport(item)}
                  style={{
                    borderBottom: idx < items.length - 1 ? '1px solid #f1f5f9' : 'none',
                    cursor: 'pointer',
                    transition: 'background-color 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#f8fafc';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  <td style={{ padding: '12px 14px' }}>{getStatusBadge(item.overall_status)}</td>
                  <td style={{ padding: '12px 14px', fontFamily: 'var(--font-mono, monospace)', fontSize: '11px', color: '#475569' }}>
                    <span title={item.id}>{item.id.slice(0, 8)}...</span>
                  </td>
                  <td style={{ padding: '12px 14px', fontWeight: 600, color: '#1e293b' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <FolderGit2 size={13} style={{ color: '#0284c7' }} />
                      <span>{item.project_name || item.project_id.slice(0, 10)}</span>
                    </div>
                  </td>
                  <td style={{ padding: '12px 14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontFamily: 'var(--font-mono, monospace)', fontSize: '11.5px', color: '#334155' }}>
                      <FileCode size={13} style={{ color: '#64748b' }} />
                      <span>{item.file_path}</span>
                    </div>
                  </td>
                  <td style={{ padding: '12px 14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span
                        style={{
                          fontFamily: 'var(--font-mono, monospace)',
                          fontSize: '10.5px',
                          fontWeight: 700,
                          backgroundColor: '#eff6ff',
                          color: '#1d4ed8',
                          padding: '1px 5px',
                          borderRadius: '3px',
                        }}
                      >
                        {item.rule_id || item.comparison?.target_rule_id || 'RULE'}
                      </span>
                      <span style={{ fontSize: '11px', color: item.target_bug_status === 'resolved' ? '#16a34a' : '#dc2626', fontWeight: 600 }}>
                        {item.target_bug_status.toUpperCase()}
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: '12px 14px' }}>
                    {item.comparison?.regression_count > 0 ? (
                      <span style={{ color: '#dc2626', fontWeight: 700, fontSize: '11.5px' }}>
                        +{item.comparison.regression_count} new bugs
                      </span>
                    ) : (
                      <span style={{ color: '#16a34a', fontWeight: 600, fontSize: '11.5px' }}>
                        0 regressions
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '12px 14px', color: '#64748b', fontSize: '11.5px' }}>
                    {item.duration_ms.toFixed(1)}ms
                  </td>
                  <td style={{ padding: '12px 14px', color: '#64748b', fontSize: '11.5px' }}>
                    {new Date(item.created_at).toLocaleString()}
                  </td>
                  <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedReport(item);
                      }}
                      data-testid={`view-report-btn-${item.id}`}
                      style={{
                        padding: '4px 10px',
                        backgroundColor: '#f1f5f9',
                        color: '#0284c7',
                        border: '1px solid #cbd5e1',
                        borderRadius: '4px',
                        fontSize: '11.5px',
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >
                      View Report
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 16px',
                borderTop: '1px solid #e2e8f0',
                backgroundColor: '#f8fafc',
                fontSize: '12px',
                color: '#64748b',
              }}
            >
              <div>
                Showing {(currentPage - 1) * pageSize + 1} to {Math.min(totalCount, currentPage * pageSize)} of {totalCount} records
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  data-testid="prev-page-btn"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '4px 10px',
                    border: '1px solid #cbd5e1',
                    borderRadius: '4px',
                    backgroundColor: '#ffffff',
                    cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                    color: currentPage === 1 ? '#94a3b8' : '#1e293b',
                  }}
                >
                  <ChevronLeft size={14} />
                  <span>Prev</span>
                </button>

                <span>
                  Page {currentPage} of {totalPages}
                </span>

                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  data-testid="next-page-btn"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '4px 10px',
                    border: '1px solid #cbd5e1',
                    borderRadius: '4px',
                    backgroundColor: '#ffffff',
                    cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                    color: currentPage === totalPages ? '#94a3b8' : '#1e293b',
                  }}
                >
                  <span>Next</span>
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          6. DETAILED VERIFICATION REPORT MODAL
         ========================================================================= */}
      {selectedReport && (
        <Modal
          isOpen={Boolean(selectedReport)}
          onClose={() => setSelectedReport(null)}
          title={`Verification Report: ${selectedReport.file_path}`}
          maxWidth="860px"
        >
          <div style={{ maxHeight: '75vh', overflowY: 'auto' }}>
            <RepairVerificationCard
              report={selectedReport}
              projectId={selectedReport.project_id}
              proposalId={selectedReport.proposal_id}
              onClose={() => setSelectedReport(null)}
            />
          </div>
        </Modal>
      )}
    </div>
  );
};
