import { RouteObject } from 'react-router-dom';
import { DashboardPage } from '../pages/DashboardPage';
import { NewAnalysisPage } from '../pages/NewAnalysisPage';
import { ComingSoonPage } from '../pages/ComingSoonPage';
import { StatusState } from '../components/common/StatusIndicator';

export const getRoutes = (onConnectionChange?: (state: StatusState) => void): RouteObject[] => [
  {
    path: '/',
    element: <DashboardPage onConnectionChange={onConnectionChange} />,
  },
  {
    path: '/analysis',
    element: <NewAnalysisPage />,
  },
  {
    path: '/projects',
    element: <ComingSoonPage moduleName="Projects" phase="Phase 2" />,
  },
  {
    path: '/repairs',
    element: <ComingSoonPage moduleName="Code Repairs" phase="Phase 3" />,
  },
  {
    path: '/test-results',
    element: <ComingSoonPage moduleName="Test Results" phase="Phase 3" />,
  },
  {
    path: '/analytics',
    element: <ComingSoonPage moduleName="Analytics" phase="Phase 4" />,
  },
  {
    path: '/history',
    element: <ComingSoonPage moduleName="History" phase="Phase 4" />,
  },
  {
    path: '/settings',
    element: <ComingSoonPage moduleName="Settings" phase="Phase 4" />,
  },
];
