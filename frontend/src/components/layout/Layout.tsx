import React from 'react';
import { Sidebar } from './Sidebar';
import { Navbar } from './Navbar';
import { StatusState } from '../common/StatusIndicator';

interface LayoutProps {
  children: React.ReactNode;
  pageTitle: string;
  connectionState: StatusState;
  onRetryConnection?: () => void;
  isRetrying?: boolean;
}

export const Layout: React.FC<LayoutProps> = ({
  children,
  pageTitle,
  connectionState,
  onRetryConnection,
  isRetrying,
}) => {
  return (
    <div className="app-container">
      <Sidebar />
      <div className="main-wrapper">
        <Navbar
          pageTitle={pageTitle}
          connectionState={connectionState}
          onRetryConnection={onRetryConnection}
          isRetrying={isRetrying}
        />
        <main className="content-container">{children}</main>
      </div>
    </div>
  );
};
