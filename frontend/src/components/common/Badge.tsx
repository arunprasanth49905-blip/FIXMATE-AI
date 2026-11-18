import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'neutral' | 'blue' | 'success' | 'warning' | 'danger';
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'neutral' }) => {
  const getStyle = (): React.CSSProperties => {
    switch (variant) {
      case 'blue':
        return { backgroundColor: 'var(--color-blue-subtle)', color: 'var(--color-blue-primary)', border: '1px solid var(--color-blue-border)' };
      case 'success':
        return { backgroundColor: 'var(--color-green-subtle)', color: 'var(--color-green-success)', border: '1px solid var(--color-green-border)' };
      case 'warning':
        return { backgroundColor: 'var(--color-amber-subtle)', color: 'var(--color-amber-warning)', border: '1px solid var(--color-amber-border)' };
      case 'danger':
        return { backgroundColor: 'var(--color-red-subtle)', color: 'var(--color-red-danger)', border: '1px solid var(--color-red-border)' };
      case 'neutral':
      default:
        return { backgroundColor: 'var(--color-surface-subtle)', color: 'var(--color-navy-600)', border: '1px solid var(--color-border)' };
    }
  };

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '11px',
        fontWeight: 600,
        fontFamily: 'var(--font-mono)',
        ...getStyle(),
      }}
    >
      {children}
    </span>
  );
};
