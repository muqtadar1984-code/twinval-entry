import axios, { AxiosInstance } from "axios";

import type {
  AccessGrant,
  AccessGrantCreate,
  ChainAuditResult,
  DashboardResponse,
  LoginRequest,
  LoginResponse,
  MeResponse,
  Observation,
  ObservationListItem,
  ObservationVerifyResult,
  OwnerProfile,
  OwnerProfileCreate,
  OwnerProfileUpdate,
  Page,
  Property,
  PropertyCreate,
  SensorZone,
  SensorZoneCreate,
  Severity,
  Stream,
  User,
  UserRegister,
  UUID,
} from "../types/api";

// In dev, leave VITE_API_BASE_URL empty and rely on the vite proxy.
// In prod, set it to the backend origin.
const baseURL = import.meta.env.VITE_API_BASE_URL || "/api";

const http: AxiosInstance = axios.create({
  baseURL,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Surface 401s in a way the auth context can react to.
http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      window.dispatchEvent(new CustomEvent("twinval:unauthorized"));
    }
    return Promise.reject(err);
  }
);

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const auth = {
  login: (body: LoginRequest) =>
    http.post<LoginResponse>("/auth/login", body).then((r) => r.data),
  me: () => http.get<MeResponse>("/auth/me").then((r) => r.data),
  refresh: () => http.post("/auth/refresh").then((r) => r.data),
  logout: () => http.post("/auth/logout").then((r) => r.data),
};

// ---------------------------------------------------------------------------
// Owner profiles
// ---------------------------------------------------------------------------

export const ownerProfiles = {
  create: (body: OwnerProfileCreate) =>
    http.post<OwnerProfile>("/owner-profiles", body).then((r) => r.data),
  list: (params?: { stream?: Stream; limit?: number; offset?: number }) =>
    http
      .get<Page<OwnerProfile>>("/owner-profiles", { params })
      .then((r) => r.data),
  get: (id: UUID) =>
    http.get<OwnerProfile>(`/owner-profiles/${id}`).then((r) => r.data),
  update: (id: UUID, body: OwnerProfileUpdate) =>
    http
      .patch<OwnerProfile>(`/owner-profiles/${id}`, body)
      .then((r) => r.data),
};

// ---------------------------------------------------------------------------
// Properties
// ---------------------------------------------------------------------------

export const properties = {
  create: (body: PropertyCreate) =>
    http.post<Property>("/properties", body).then((r) => r.data),
  list: (params?: { stream?: Stream; status?: string; limit?: number; offset?: number }) =>
    http.get<Page<Property>>("/properties", { params }).then((r) => r.data),
  get: (id: UUID) =>
    http.get<Property>(`/properties/${id}`).then((r) => r.data),
};

// ---------------------------------------------------------------------------
// Sensor zones
// ---------------------------------------------------------------------------

export const sensorZones = {
  create: (body: SensorZoneCreate) =>
    http.post<SensorZone>("/sensor-zones", body).then((r) => r.data),
  list: (propertyId: UUID, params?: { limit?: number; offset?: number }) =>
    http
      .get<Page<SensorZone>>("/sensor-zones", {
        params: { property_id: propertyId, ...params },
      })
      .then((r) => r.data),
};

// ---------------------------------------------------------------------------
// Observations
// ---------------------------------------------------------------------------

export interface ObservationSubmit {
  property_id: UUID;
  sensor_zone_id: UUID;
  observation_type: string;
  description: string;
  severity: Severity;
  photo?: File | null;
}

export const observations = {
  submit: (body: ObservationSubmit) => {
    const fd = new FormData();
    fd.append("property_id", body.property_id);
    fd.append("sensor_zone_id", body.sensor_zone_id);
    fd.append("observation_type", body.observation_type);
    fd.append("description", body.description);
    fd.append("severity", body.severity);
    if (body.photo) fd.append("photo", body.photo);
    return http
      .post<Observation>("/observations", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
  list: (params?: {
    severity?: Severity;
    property_id?: UUID;
    limit?: number;
    offset?: number;
  }) =>
    http
      .get<Page<ObservationListItem>>("/observations", { params })
      .then((r) => r.data),
  get: (id: UUID) =>
    http.get<Observation>(`/observations/${id}`).then((r) => r.data),
  verify: (id: UUID) =>
    http
      .get<ObservationVerifyResult>(`/observations/${id}/verify`)
      .then((r) => r.data),
};

// ---------------------------------------------------------------------------
// Admin
// ---------------------------------------------------------------------------

export const admin = {
  observations: (params?: {
    severity?: Severity;
    stream?: Stream;
    property_id?: UUID;
    intern_id?: UUID;
    submitted_from?: string;
    submitted_to?: string;
    reviewed?: boolean;
    limit?: number;
    offset?: number;
  }) =>
    http
      .get<Page<ObservationListItem>>("/admin/observations", { params })
      .then((r) => r.data),
  review: (id: UUID, reviewer_note: string | null) =>
    http
      .patch<Observation>(`/admin/observations/${id}/review`, { reviewer_note })
      .then((r) => r.data),
  void: (id: UUID, reason: string) =>
    http
      .patch<Observation>(`/admin/observations/${id}/void`, { reason })
      .then((r) => r.data),
  chainVerify: () =>
    http.get<ChainAuditResult>("/admin/chain/verify").then((r) => r.data),
  dashboardProperties: (params?: {
    stream?: Stream[];
    severity?: Severity[];
    property_status?: string;
    kyc_status?: string;
    submitted_from?: string;
    submitted_to?: string;
    search?: string;
    all?: boolean;
  }) => {
    // axios serialises array params with `?key=a&key=b` when paramsSerializer
    // is given; the default repeats — which is what FastAPI expects.
    const flat: Record<string, string | string[] | boolean | undefined> = {};
    if (params?.stream) flat.stream = params.stream;
    if (params?.severity) flat.severity = params.severity;
    if (params?.property_status) flat.property_status = params.property_status;
    if (params?.kyc_status) flat.kyc_status = params.kyc_status;
    if (params?.submitted_from) flat.submitted_from = params.submitted_from;
    if (params?.submitted_to) flat.submitted_to = params.submitted_to;
    if (params?.search) flat.search = params.search;
    if (params?.all) flat.all = "true";
    return http
      .get<DashboardResponse>("/admin/dashboard/properties", {
        params: flat,
        paramsSerializer: { indexes: null },
      })
      .then((r) => r.data);
  },
  registerUser: (body: UserRegister) =>
    http.post<User>("/admin/users", body).then((r) => r.data),
  listUsers: (params?: { limit?: number; offset?: number }) =>
    http.get<Page<User>>("/admin/users", { params }).then((r) => r.data),
  createGrant: (body: AccessGrantCreate) =>
    http.post<AccessGrant>("/admin/access-grants", body).then((r) => r.data),
  listGrants: (params?: { user_id?: UUID; limit?: number; offset?: number }) =>
    http
      .get<Page<AccessGrant>>("/admin/access-grants", { params })
      .then((r) => r.data),
  revokeGrant: (id: UUID) =>
    http.delete(`/admin/access-grants/${id}`).then(() => undefined),
};
