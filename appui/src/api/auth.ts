import { API_ROUTES } from '.';
import { http } from './http';

export type UserRole = 'admin' | 'user';

export interface AuthUser {
  email: string;
  role: UserRole;
}

export interface AuthCredentials {
  email: string;
  password: string;
}

export interface AuthSession {
  access_token: string;
  token_type: 'bearer';
  user: AuthUser;
}

export function registerUser(credentials: AuthCredentials) {
  return http.post<AuthSession, AuthCredentials>(API_ROUTES.authRegister, credentials);
}

export function loginUser(credentials: AuthCredentials) {
  return http.post<AuthSession, AuthCredentials>(API_ROUTES.authLogin, credentials);
}

export function fetchCurrentUser(token?: string) {
  return http.get<AuthUser>(
    API_ROUTES.authMe,
    token
      ? {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      : undefined,
  );
}
