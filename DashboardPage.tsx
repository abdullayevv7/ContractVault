/**
 * Authentication API service.
 * Handles login, registration, profile, and password management.
 */
import apiClient from "./client";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
}

export interface AuthResponse {
  success: boolean;
  user: UserProfile;
  tokens: {
    access: string;
    refresh: string;
  };
}

export interface UserProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  job_title: string;
  department: string;
  avatar: string | null;
  timezone: string;
  organization: OrganizationInfo | null;
  role: RoleInfo | null;
  email_notifications: boolean;
  is_active: boolean;
  date_joined: string;
}

export interface OrganizationInfo {
  id: string;
  name: string;
  slug: string;
}

export interface RoleInfo {
  id: string;
  name: string;
  role_type: string;
}

export const authApi = {
  login(payload: LoginPayload) {
    return apiClient.post<AuthResponse>("/auth/login/", payload);
  },

  register(payload: RegisterPayload) {
    return apiClient.post<AuthResponse>("/auth/register/", payload);
  },

  getProfile() {
    return apiClient.get<UserProfile>("/auth/profile/");
  },

  updateProfile(data: Partial<UserProfile>) {
    return apiClient.patch<UserProfile>("/auth/profile/", data);
  },

  changePassword(oldPassword: string, newPassword: string) {
    return apiClient.post("/auth/change-password/", {
      old_password: oldPassword,
      new_password: newPassword,
    });
  },

  refreshToken(refreshToken: string) {
    return apiClient.post<{ access: string; refresh?: string }>(
      "/auth/refresh/",
      { refresh: refreshToken },
    );
  },
};
