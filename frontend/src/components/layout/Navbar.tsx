import React from 'react';
import { StatusIndicator, StatusState } from '../common/StatusIndicator';

interface NavbarProps {
  pageTitle: string;
  connectionState: StatusState;
  onRetryConnection?: () => void;
  isRetrying?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  pageTitle,
  connectionState,
  onRetryConnection,
  isRetrying = false,
}) => {
  return (
    <header className="navbar">
      <div className="navbar-left">
        <h1 className="page-title">{pageTitle}</h1>
      </div>
      <div className="navbar-right">
        <StatusIndicator
          state={connectionState}
          onRetry={onRetryConnection}
          isRetrying={isRetrying}
        />
      </div>
    </header>
  );
};
