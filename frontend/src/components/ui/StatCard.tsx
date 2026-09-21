import React from 'react';
import clsx from 'clsx';
import { Card } from './Card';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    value: string;
    isPositive?: boolean;
    label?: string;
  };
  badgeText?: string;
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  badgeText,
  className,
}) => {
  return (
    <Card className={clsx('relative p-4 liquid-glass border border-white/85 shadow-sm', className)}>
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-0.5 min-w-0">
          <p className="text-[10.5px] font-bold text-slate-500 uppercase tracking-wider truncate">
            {title}
          </p>
          <div className="flex items-baseline gap-2 pt-0.5">
            <h3 className="text-xl sm:text-2xl font-extrabold tracking-tight text-slate-900 font-mono">
              {value}
            </h3>
            {badgeText && (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-white/70 text-slate-700 border border-white/90 backdrop-blur-md shadow-2xs">
                {badgeText}
              </span>
            )}
          </div>
        </div>

        {icon && (
          <div className="p-2 rounded-xl bg-white/60 border border-white/80 text-slate-700 backdrop-blur-md shadow-2xs shrink-0">
            {icon}
          </div>
        )}
      </div>

      {(subtitle || trend) && (
        <div className="mt-2.5 pt-2 border-t border-slate-200/50 flex items-center justify-between text-xs gap-2">
          {subtitle && <span className="text-slate-500 truncate text-[11px] font-normal">{subtitle}</span>}
          {trend && (
            <div className="flex items-center gap-1.5 ml-auto shrink-0">
              <span
                className={clsx(
                  'inline-flex items-center text-[10px] font-bold px-2 py-0.5 rounded-full border backdrop-blur-md',
                  trend.isPositive
                    ? 'text-indigo-800 bg-indigo-50 border-indigo-200'
                    : 'text-rose-800 bg-rose-50 border-rose-200'
                )}
              >
                {trend.value}
              </span>
              {trend.label && <span className="text-slate-400 text-[10px]">{trend.label}</span>}
            </div>
          )}
        </div>
      )}
    </Card>
  );
};
