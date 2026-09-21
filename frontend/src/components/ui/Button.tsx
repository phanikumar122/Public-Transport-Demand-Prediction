import React from 'react';
import clsx from 'clsx';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'mint' | 'ice' | 'lemon';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  className,
  disabled,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-semibold rounded-lg transition-all focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed select-none';

  const variantStyles = {
    primary: 'bg-crimson-500 hover:bg-crimson-600 text-white shadow-sm shadow-crimson-500/30 active:scale-[0.98]',
    secondary: 'bg-periwinkle-100 hover:bg-periwinkle-200 text-slate-800 border border-periwinkle-300 active:scale-[0.98]',
    outline: 'bg-white hover:bg-periwinkle-50 text-slate-800 border border-periwinkle-300 hover:border-crimson-400 shadow-xs active:scale-[0.98]',
    ghost: 'bg-transparent hover:bg-periwinkle-100 text-slate-700 hover:text-slate-900',
    danger: 'bg-crimson-700 hover:bg-crimson-800 text-white shadow-sm shadow-crimson-700/30 active:scale-[0.98]',
    mint: 'bg-tropicalmint-500 hover:bg-tropicalmint-600 text-slate-950 shadow-sm shadow-tropicalmint-500/30 active:scale-[0.98]',
    ice: 'bg-neonice-500 hover:bg-neonice-600 text-slate-950 shadow-sm shadow-neonice-500/30 active:scale-[0.98]',
    lemon: 'bg-lemon-400 hover:bg-lemon-500 text-slate-950 shadow-sm shadow-lemon-400/30 active:scale-[0.98]',
  };

  const sizeStyles = {
    sm: 'text-xs px-3 py-1.5 gap-1.5',
    md: 'text-xs px-4 py-2 gap-2',
    lg: 'text-sm px-5 py-2.5 gap-2.5',
  };

  return (
    <button
      className={clsx(baseStyles, variantStyles[variant], sizeStyles[size], className)}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
};
