import React, { useEffect, useState, useCallback } from 'react';
import { apiClient } from '../services/apiClient';
import { HealthResponse, SystemInfoResponse, AIStatusResponse, AITestResponse } from '../types/api';
import { StatusState } from '../components/common/StatusIndicator';
import { WelcomeSection } from '../components/dashboard/WelcomeSection';
import { SystemStatusCard } from '../components/dashboard/SystemStatusCard';
import { GeminiTestCard } from '../components/dashboard/GeminiTestCard';
import { ProjectOverviewCard } from '../components/dashboard/ProjectOverviewCard';
import { RecentActivityCard } from '../components/dashboard/RecentActivityCard';

interface DashboardPageProps {
  onConnectionChange?: (state: StatusState) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onConnectionChange }) => {
  // MUST start at 'checking', NEVER 'connected' by default
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [aiStatus, setAiStatus] = useState<AIStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const updateConnection = useCallback((state: StatusState) => {
    if (onConnectionChange) {
      onConnectionChange(state);
    }
  }, [onConnectionChange]);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    updateConnection('checking');
    setError(null);

    try {
      // 1. Health check
      const healthData = await apiClient.getHealth();
      setHealth(healthData);

      // 2. System info & AI status in parallel
      const [infoData, aiData] = await Promise.all([
        apiClient.getSystemInfo(),
        apiClient.getAIStatus(),
      ]);

      setSystemInfo(infoData);
      setAiStatus(aiData);
      updateConnection('connected');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to reach backend';
      setError(message);
      setHealth(null);
      setSystemInfo(null);
      setAiStatus(null);
      updateConnection('disconnected');
    } finally {
      setIsLoading(false);
    }
  }, [updateConnection]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleTestAI = async (): Promise<AITestResponse> => {
    return apiClient.testAIConnection();
  };

  const handleRefreshAIStatus = async () => {
    try {
      const updated = await apiClient.getAIStatus();
      setAiStatus(updated);
    } catch {
      // Retain existing view if status refresh fails
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <WelcomeSection />

      <div className="grid-2">
        <SystemStatusCard
          health={health}
          systemInfo={systemInfo}
          aiStatus={aiStatus}
          isLoading={isLoading}
          error={error}
        />

        <GeminiTestCard
          aiStatus={aiStatus}
          onRunTest={handleTestAI}
          onRefreshStatus={handleRefreshAIStatus}
        />
      </div>

      <ProjectOverviewCard />

      <RecentActivityCard />
    </div>
  );
};
