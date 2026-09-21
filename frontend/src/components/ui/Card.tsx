import React from 'react';
import clsx from 'clsx';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  variant?: 'glass' | 'subtle' | 'panel' | 'solid';
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  hover = false,
  variant = 'glass',
  ...props
}) => {
  const variantStyles = {
    glass: 'liquid-glass',
    subtle: 'liquid-glass-subtle',
    panel: 'liquid-glass-panel',
    solid: 'bg-white border border-slate-200/80 shadow-2xs rounded-xl',
  };

  return (
    <div
      className={clsx(
        variantStyles[variant],
        hover && 'liquid-glass-interactive cursor-pointer',
        'p-4 text-slate-900',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};
