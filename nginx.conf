/**
 * DashboardStats component.
 * Displays key metrics cards for the analytics dashboard.
 */
import React from "react";
import { formatCurrency } from "../utils/formatters";

export interface DashboardData {
  total_contracts: number;
  active_contracts: number;
  draft_contracts: number;
  total_value: string;
  pending_approvals: number;
  pending_signatures: number;
  expiring_in_30_days: number;
  expiring_in_90_days: number;
}

interface Props {
  data: DashboardData | null;
  isLoading: boolean;
}

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  accentColor?: string;
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  accentColor = "blue",
}) => (
  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
    <p className="text-sm font-medium text-gray-500 mb-1">{title}</p>
    <p className={`text-2xl font-bold text-${accentColor}-600`}>{value}</p>
    {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
  </div>
);

const DashboardStats: React.FC<Props> = ({ data, isLoading }) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="bg-white rounded-lg shadow-sm border border-gray-200 p-5 animate-pulse"
          >
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-2" />
            <div className="h-8 bg-gray-200 rounded w-3/4" />
          </div>
        ))}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        title="Total Contracts"
        value={data.total_contracts}
        accentColor="gray"
      />
      <StatCard
        title="Active Contracts"
        value={data.active_contracts}
        accentColor="green"
      />
      <StatCard
        title="Total Portfolio Value"
        value={formatCurrency(data.total_value)}
        accentColor="blue"
      />
      <StatCard
        title="Draft Contracts"
        value={data.draft_contracts}
        accentColor="gray"
      />
      <StatCard
        title="Pending Approvals"
        value={data.pending_approvals}
        subtitle="Awaiting review"
        accentColor="yellow"
      />
      <StatCard
        title="Pending Signatures"
        value={data.pending_signatures}
        subtitle="Awaiting signature"
        accentColor="purple"
      />
      <StatCard
        title="Expiring in 30 Days"
        value={data.expiring_in_30_days}
        subtitle="Needs attention"
        accentColor="orange"
      />
      <StatCard
        title="Expiring in 90 Days"
        value={data.expiring_in_90_days}
        subtitle="Upcoming renewals"
        accentColor="yellow"
      />
    </div>
  );
};

export default DashboardStats;
