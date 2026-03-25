/**
 * ContractFilters component.
 * Provides search, status, and priority filter controls for the contract list.
 */
import React, { useState, useCallback } from "react";
import { ContractFilters as FilterType } from "../api/contracts";

interface Props {
  onFilterChange: (filters: FilterType) => void;
  initialFilters?: FilterType;
}

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "draft", label: "Draft" },
  { value: "pending_approval", label: "Pending Approval" },
  { value: "approved", label: "Approved" },
  { value: "active", label: "Active" },
  { value: "expired", label: "Expired" },
  { value: "terminated", label: "Terminated" },
  { value: "archived", label: "Archived" },
];

const PRIORITY_OPTIONS = [
  { value: "", label: "All Priorities" },
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

const SORT_OPTIONS = [
  { value: "-created_at", label: "Newest First" },
  { value: "created_at", label: "Oldest First" },
  { value: "-total_value", label: "Highest Value" },
  { value: "total_value", label: "Lowest Value" },
  { value: "expiration_date", label: "Expiring Soonest" },
  { value: "title", label: "Title A-Z" },
];

const ContractFilters: React.FC<Props> = ({
  onFilterChange,
  initialFilters = {},
}) => {
  const [search, setSearch] = useState(initialFilters.search || "");
  const [statusFilter, setStatusFilter] = useState(initialFilters.status || "");
  const [priorityFilter, setPriorityFilter] = useState(
    initialFilters.priority || "",
  );
  const [ordering, setOrdering] = useState(
    initialFilters.ordering || "-created_at",
  );

  const applyFilters = useCallback(() => {
    const filters: FilterType = { ordering };
    if (search.trim()) filters.search = search.trim();
    if (statusFilter) filters.status = statusFilter;
    if (priorityFilter) filters.priority = priorityFilter;
    onFilterChange(filters);
  }, [search, statusFilter, priorityFilter, ordering, onFilterChange]);

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") applyFilters();
  };

  const handleReset = () => {
    setSearch("");
    setStatusFilter("");
    setPriorityFilter("");
    setOrdering("-created_at");
    onFilterChange({});
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Search */}
        <div className="lg:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Search
          </label>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            placeholder="Search by title, number, or description..."
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Status */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Status
          </label>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
            }}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Priority */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Priority
          </label>
          <select
            value={priorityFilter}
            onChange={(e) => {
              setPriorityFilter(e.target.value);
            }}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
          >
            {PRIORITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Sort */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Sort By
          </label>
          <select
            value={ordering}
            onChange={(e) => {
              setOrdering(e.target.value);
            }}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex justify-end gap-3 mt-4">
        <button
          onClick={handleReset}
          className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Reset
        </button>
        <button
          onClick={applyFilters}
          className="px-4 py-2 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700"
        >
          Apply Filters
        </button>
      </div>
    </div>
  );
};

export default ContractFilters;
