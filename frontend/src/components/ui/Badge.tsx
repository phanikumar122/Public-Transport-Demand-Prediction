import React from 'react';
import clsx from 'clsx';

export type BadgeVariant =
  | 'primary'
  | 'crimson'
  | 'mint'
  | 'ice'
  | 'periwinkle'
  | 'lemon'
  | 'success'
  | 'warning'
  | 'danger'
  | 'purple'
  | 'neutral'
  | 'blue'
  | 'emerald'
  | 'rose'
  | 'indigo'
  | 'outline'
  | 'default';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  className,
  dot = false,
}) => {
  const variantStyles: Record<BadgeVariant, string> = {
    primary: 'bg-rose-500/10 text-rose-700 border-rose-400/30 backdrop-blur-md',
    crimson: 'bg-rose-500/10 text-rose-700 border-rose-400/30 backdrop-blur-md',
    mint: 'bg-sky-500/10 text-sky-800 border-sky-400/30 backdrop-blur-md',
    ice: 'bg-cyan-500/10 text-cyan-800 border-cyan-400/30 backdrop-blur-md',
    periwinkle: 'bg-indigo-500/10 text-indigo-800 border-indigo-400/30 backdrop-blur-md',
    lemon: 'bg-amber-500/15 text-amber-900 border-amber-400/40 backdrop-blur-md font-semibold',
    indigo: 'bg-indigo-500/10 text-indigo-800 border-indigo-400/30 backdrop-blur-md',
    blue: 'bg-blue-500/10 text-blue-800 border-blue-400/30 backdrop-blur-md',
    success: 'bg-sky-500/10 text-sky-800 border-sky-400/30 backdrop-blur-md',
    emerald: 'bg-sky-500/10 text-sky-800 border-sky-400/30 backdrop-blur-md',
    warning: 'bg-amber-500/15 text-amber-900 border-amber-400/40 backdrop-blur-md',
    danger: 'bg-rose-500/12 text-rose-800 border-rose-400/40 backdrop-blur-md',
    rose: 'bg-rose-500/12 text-rose-800 border-rose-400/40 backdrop-blur-md',
    purple: 'bg-purple-500/10 text-purple-800 border-purple-400/30 backdrop-blur-md',
    neutral: 'bg-slate-200/50 text-slate-700 border-slate-300/60 backdrop-blur-md',
    outline: 'bg-white/40 text-slate-700 border-slate-300/80 backdrop-blur-md',
    default: 'bg-slate-200/50 text-slate-700 border-slate-300/60 backdrop-blur-md',
  };

  const dotColors: Record<BadgeVariant, string> = {
    primary: 'bg-rose-500',
    crimson: 'bg-rose-500',
    mint: 'bg-sky-500',
    ice: 'bg-cyan-500',
    periwinkle: 'bg-indigo-500',
    lemon: 'bg-amber-500',
    indigo: 'bg-indigo-500',
    blue: 'bg-blue-500',
    success: 'bg-sky-500',
    emerald: 'bg-sky-500',
    warning: 'bg-amber-500',
    danger: 'bg-rose-500',
    rose: 'bg-rose-500',
    purple: 'bg-purple-500',
    neutral: 'bg-slate-400',
    outline: 'bg-slate-400',
    default: 'bg-slate-500',
  };

  const sizeStyles = {
    sm: 'text-[10.5px] px-2 py-0.5',
    md: 'text-[11.5px] px-2.5 py-0.5',
    lg: 'text-xs px-3 py-1',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full font-medium border shadow-2xs transition-all',
        variantStyles[variant] || variantStyles.primary,
        sizeStyles[size],
        className
      )}
    >
      {dot && <span className={clsx('w-1.5 h-1.5 rounded-full', dotColors[variant] || dotColors.primary)} />}
      {children}
    </span>
  );
};
