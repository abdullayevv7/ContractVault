/**
 * Contract API service.
 * Wraps all contract-related endpoints.
 */
import apiClient from "./client";

export interface ContractListItem {
  id: string;
  contract_number: string;
  title: string;
  status: string;
  priority: string;
  contract_type: string | null;
  contract_type_name: string | null;
  total_value: string | null;
  currency: string;
  effective_date: string | null;
  expiration_date: string | null;
  days_until_expiration: number | null;
  version: number;
  created_by_name: string;
  party_count: number;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface ContractDetail extends ContractListItem {
  description: string;
  organization: string;
  termination_date: string | null;
  renewal_date: string | null;
  auto_renew: boolean;
  renewal_period_days: number | null;
  document: string | null;
  pdf_file: string | null;
  parent_contract: string | null;
  compliance_requirements: string[];
  metadata: Record<string, unknown>;
  parties: ContractParty[];
  clauses: ContractClause[];
  is_expired: boolean;
}

export interface ContractParty {
  id: string;
  name: string;
  email: string;
  phone: string;
  organization_name: string;
  role: string;
  address: string;
  is_primary: boolean;
}

export interface ContractClause {
  id: string;
  title: string;
  content: string;
  clause_type: string;
  order: number;
  is_active: boolean;
}

export interface PaginatedResponse<T> {
  count: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ContractFilters {
  status?: string;
  priority?: string;
  contract_type?: string;
  search?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export const contractsApi = {
  list(filters: ContractFilters = {}) {
    return apiClient.get<PaginatedResponse<ContractListItem>>("/contracts/", {
      params: filters,
    });
  },

  get(id: string) {
    return apiClient.get<ContractDetail>(`/contracts/${id}/`);
  },

  create(data: Partial<ContractDetail>) {
    return apiClient.post<ContractDetail>("/contracts/", data);
  },

  update(id: string, data: Partial<ContractDetail>) {
    return apiClient.patch<ContractDetail>(`/contracts/${id}/`, data);
  },

  delete(id: string) {
    return apiClient.delete(`/contracts/${id}/`);
  },

  transition(id: string, status: string) {
    return apiClient.post(`/contracts/${id}/transition/`, { status });
  },

  createVersion(id: string, changeSummary: string) {
    return apiClient.post(`/contracts/${id}/create_version/`, {
      change_summary: changeSummary,
    });
  },

  getVersions(id: string) {
    return apiClient.get(`/contracts/${id}/versions/`);
  },

  generatePdf(id: string) {
    return apiClient.post(`/contracts/${id}/generate_pdf/`, null, {
      responseType: "blob",
    });
  },

  duplicate(id: string) {
    return apiClient.post<ContractDetail>(`/contracts/${id}/duplicate/`);
  },

  submitForApproval(id: string) {
    return apiClient.post(`/contracts/${id}/submit_for_approval/`);
  },
};

export const contractTypesApi = {
  list() {
    return apiClient.get<PaginatedResponse<{ id: string; name: string; prefix: string }>>(
      "/contracts/types/",
    );
  },

  create(data: { name: string; prefix: string; description?: string }) {
    return apiClient.post("/contracts/types/", data);
  },
};
