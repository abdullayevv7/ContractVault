/**
 * ContractCard component.
 * Displays a contract summary in a card layout for list/grid views.
 */
import React from "react";
import { ContractListItem } from "../api/contracts";
import ContractStatusBadge from "./ContractStatusBadge";
import {
  formatDate,
  formatCurrency,
  getPriorityLabel,
} from "../utils/formatters";

interface Props {
  contract: ContractListItem;
  onClick?: (id: string) => void;
}

const ContractCard: React.FC<Props> = ({ contract, onClick }) => {
  const expirationWarning =
    contract.days_until_expiration !== null &&
    contract.days_until_expiration <= 30 &&
    contract.days_until_expiration > 0;

  return (
    <div
      className="bg-white rounded-lg shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => onClick?.(contract.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onClick?.(contract.id);
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <p className="text-xs text-gray-500 font-mono">
            {contract.contract_number}
          </p>
          <h3 className="text-sm font-semibold text-gray-900 truncate mt-1">
            {contract.title}
          </h3>
        </div>
        <ContractStatusBadge status={contract.status} className="ml-2" />
      </div>

      {/* Body */}
      <div className="space-y-2 text-sm text-gray-600">
        {contract.contract_type_name && (
          <div className="flex justify-between">
            <span>Type</span>
            <span className="font-medium text-gray-800">
              {contract.contract_type_name}
            </span>
          </div>
        )}
        <div className="flex justify-between">
          <span>Priority</span>
          <span className="font-medium text-gray-800">
            {getPriorityLabel(contract.priority)}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Value</span>
          <span className="font-medium text-gray-800">
            {formatCurrency(contract.total_value, contract.currency)}
          </span>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
        <span>Expires: {formatDate(contract.expiration_date)}</span>
        {expirationWarning && (
          <span className="text-orange-600 font-medium">
            {contract.days_until_expiration}d left
          </span>
        )}
        {contract.party_count > 0 && (
          <span>
            {contract.party_count} part{contract.party_count !== 1 ? "ies" : "y"}
          </span>
        )}
      </div>
    </div>
  );
};

export default ContractCard;
