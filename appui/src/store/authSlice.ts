import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';

import {
  fetchCurrentUser,
  loginUser,
  registerUser,
  type AuthCredentials,
  type AuthSession,
  type AuthUser,
} from '../api/auth';
import { setHttpAuthToken } from '../api/http';

const AUTH_TOKEN_STORAGE_KEY = 'ctp_research_auth_token';

type AuthStatus = 'anonymous' | 'authenticated' | 'hydrating' | 'loading';

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  status: AuthStatus;
  error: string | null;
}

interface HydratedSession {
  token: string;
  user: AuthUser;
}

function readStoredToken() {
  if (typeof window === 'undefined') return null;

  try {
    return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

function persistToken(token: string) {
  setHttpAuthToken(token);
  if (typeof window === 'undefined') return;

  try {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  } catch {
    // A blocked storage write should not prevent the in-memory session.
  }
}

function clearStoredToken() {
  setHttpAuthToken(null);
  if (typeof window === 'undefined') return;

  try {
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    // Nothing else to clear when browser storage is unavailable.
  }
}

function persistSession(session: AuthSession) {
  persistToken(session.access_token);
  return session;
}

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback;
}

const storedToken = readStoredToken();
setHttpAuthToken(storedToken);

const initialState: AuthState = {
  token: storedToken,
  user: null,
  status: storedToken ? 'hydrating' : 'anonymous',
  error: null,
};

export const hydrateAuthSession = createAsyncThunk<
  HydratedSession | null,
  void,
  { rejectValue: string }
>('auth/hydrateSession', async (_, { rejectWithValue }) => {
  const token = readStoredToken();
  if (!token) {
    clearStoredToken();
    return null;
  }

  try {
    setHttpAuthToken(token);
    const user = await fetchCurrentUser(token);
    return { token, user };
  } catch (error) {
    clearStoredToken();
    return rejectWithValue(getErrorMessage(error, 'Session expired'));
  }
});

export const registerWithEmail = createAsyncThunk<
  AuthSession,
  AuthCredentials,
  { rejectValue: string }
>('auth/registerWithEmail', async (credentials, { rejectWithValue }) => {
  try {
    return persistSession(await registerUser(credentials));
  } catch (error) {
    return rejectWithValue(getErrorMessage(error, 'Registration failed'));
  }
});

export const loginWithEmail = createAsyncThunk<
  AuthSession,
  AuthCredentials,
  { rejectValue: string }
>('auth/loginWithEmail', async (credentials, { rejectWithValue }) => {
  try {
    return persistSession(await loginUser(credentials));
  } catch (error) {
    return rejectWithValue(getErrorMessage(error, 'Login failed'));
  }
});

export const logout = createAsyncThunk('auth/logout', async () => {
  clearStoredToken();
});

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearAuthError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(hydrateAuthSession.pending, (state) => {
        state.status = 'hydrating';
        state.error = null;
      })
      .addCase(hydrateAuthSession.fulfilled, (state, action) => {
        if (!action.payload) {
          state.token = null;
          state.user = null;
          state.status = 'anonymous';
          return;
        }

        state.token = action.payload.token;
        state.user = action.payload.user;
        state.status = 'authenticated';
      })
      .addCase(hydrateAuthSession.rejected, (state, action) => {
        state.token = null;
        state.user = null;
        state.status = 'anonymous';
        state.error = action.payload || action.error.message || 'Session expired';
      })
      .addCase(registerWithEmail.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(registerWithEmail.fulfilled, (state, action) => {
        state.token = action.payload.access_token;
        state.user = action.payload.user;
        state.status = 'authenticated';
      })
      .addCase(registerWithEmail.rejected, (state, action) => {
        state.status = 'anonymous';
        state.error = action.payload || action.error.message || 'Registration failed';
      })
      .addCase(loginWithEmail.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(loginWithEmail.fulfilled, (state, action) => {
        state.token = action.payload.access_token;
        state.user = action.payload.user;
        state.status = 'authenticated';
      })
      .addCase(loginWithEmail.rejected, (state, action) => {
        state.status = 'anonymous';
        state.error = action.payload || action.error.message || 'Login failed';
      })
      .addCase(logout.fulfilled, (state) => {
        state.token = null;
        state.user = null;
        state.status = 'anonymous';
        state.error = null;
      });
  },
});

export const { clearAuthError } = authSlice.actions;
export default authSlice.reducer;
