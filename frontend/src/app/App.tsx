import React, { useState } from 'react';
import { useRoutes, useLocation } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { StatusState } from '../components/common/StatusIndicator';
import { getRoutes } from './routes';
import { apiClient } from '../services/apiClient';

export const App: React.FC = () => {
  const [connectionState, setConnectionState] = useState<StatusState>('checking');
  const [isRetrying, setIsRetrying] = useState<boolean>(false);
  const location = useLocation();

  const handleRetry = async () => {
    setIsRetrying(true);
    setConnectionState('checking');
    try {
      await apiClient.getHealth();
      setConnectionState('connected');
    } catch {
      setConnectionState('disconnected');
    } finally {
      setIsRetrying(false);
    }
  };

  const getPageTitle = (path: string) => {
    switch (path) {
      case '/':
        return 'Developer Dashboard';
      case '/analysis':
        return 'New Analysis Pipeline';
      case '/projects':
        return 'Projects Directory';
      case '/repairs':
        return 'Autonomous Code Repairs';
      case '/test-results':
        return 'Test & Verification Suite';
      case '/analytics':
        return 'Platform Analytics';
      case '/history':
        return 'Repair History';
      case '/settings':
        return 'System Settings';
      default:
        return 'FIXMATE AI';
    }
  };

  const routeElements = useRoutes(getRoutes(setConnectionState));

  return (
    <Layout
      pageTitle={getPageTitle(location.pathname)}
      connectionState={connectionState}
      onRetryConnection={handleRetry}
      isRetrying={isRetrying}
    >
      {routeElements}
    </Layout>
  );
};
