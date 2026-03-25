/**
 * ContractStatusBadge component.
 * Displays a coloured badge for the contract status.
 */
import React from "react";
import { getStatusLabel, getStatusColor } from "../utils/formatters";

interface Props {
  status: string;
  className?: string;
}

const ContractStatusBadge: React.FC<Props> = ({ status, className = "" }) => {
  const colorClass = getStatusColor(status);
  const label = getStatusLabel(status);

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass} ${className}`}
    >
      {label}
    </span>
  );
};

export default ContractStatusBadge;
