// Mirrors backend Pydantic schemas. Keep in sync.

export type UUID = string;

export type Stream =
  | "reit"
  | "lender"
  | "individual"
  | "insurer"
  | "government"
  | "family_office"
  | "developer";

export const STREAM_LABELS: Record<Stream, string> = {
  reit: "REIT",
  lender: "Lender",
  individual: "Individual",
  insurer: "Insurer",
  government: "Government",
  family_office: "Family Office",
  developer: "Developer",
};

export type KycStatus = "pending" | "verified" | "failed";

export type UserRole = "intern" | "admin" | "stakeholder" | "auditor";

export type Severity = "Normal" | "Watch" | "Alert";

export type ObservationType =
  | "Anomaly"
  | "Maintenance Event"
  | "Visual Inspection"
  | "Sensor Health";

export type PropertyStatus = "active" | "archived";

export type AccessScopeKind = "all" | "stream" | "owner_profile" | "property";

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  user_id: UUID;
  name: string;
  email: string;
  role: UserRole;
}

export interface MeResponse {
  id: UUID;
  name: string;
  email: string;
  role: UserRole;
}

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------------------
// Owner profiles
// ---------------------------------------------------------------------------

export interface OwnerProfile {
  id: UUID;
  stream: Stream;
  legal_name: string;
  legal_id: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  kyc_status: KycStatus;
  created_at: string;
}

export interface OwnerProfileCreate {
  stream: Stream;
  legal_name: string;
  legal_id?: string;
  contact_email?: string;
  contact_phone?: string;
}

export interface OwnerProfileUpdate {
  legal_name?: string;
  legal_id?: string;
  contact_email?: string;
  contact_phone?: string;
  kyc_status?: KycStatus;
}

// ---------------------------------------------------------------------------
// Properties
// ---------------------------------------------------------------------------

export interface Property {
  id: UUID;
  name: string;
  address: string;
  city: string | null;
  country: string | null;
  geo_lat: string | null;
  geo_lng: string | null;
  structure_value: string | null;
  land_value: string | null;
  primary_owner_id: UUID;
  primary_owner_name: string;
  primary_owner_stream: Stream;
  status: PropertyStatus;
  created_by: UUID;
  created_at: string;
}

export interface PropertyCreate {
  name: string;
  address: string;
  city?: string;
  country?: string;
  geo_lat?: number;
  geo_lng?: number;
  structure_value?: number;
  land_value?: number;
  primary_owner_id: UUID;
}

// ---------------------------------------------------------------------------
// Sensor zones
// ---------------------------------------------------------------------------

export interface SensorZone {
  id: UUID;
  property_id: UUID;
  building_label: string;
  zone_label: string;
  is_active: boolean;
  created_at: string;
}

export interface SensorZoneCreate {
  property_id: UUID;
  building_label: string;
  zone_label: string;
}

// ---------------------------------------------------------------------------
// Observations
// ---------------------------------------------------------------------------

export interface Observation {
  id: UUID;
  entry_ref_id: string;
  intern_id: UUID;
  property_id: UUID;
  sensor_zone_id: UUID;
  owner_profile_id: UUID;
  submitted_at: string;
  property_name: string;
  building_label: string;
  zone_label: string;
  owner_profile_name: string;
  stream: Stream;
  observation_type: ObservationType;
  description: string;
  severity: Severity;
  photo_url: string | null;
  entry_hash: string;
  prev_hash: string;
  chain_sequence: number;
  reviewed: boolean;
  reviewer_note: string | null;
  reviewed_by: UUID | null;
  reviewed_at: string | null;
  voided: boolean;
  voided_at: string | null;
  voided_by: UUID | null;
  void_reason: string | null;
}

export interface ObservationListItem {
  id: UUID;
  entry_ref_id: string;
  submitted_at: string;
  property_id: UUID;
  property_name: string;
  building_label: string;
  zone_label: string;
  owner_profile_name: string;
  stream: Stream;
  observation_type: ObservationType;
  severity: Severity;
  entry_hash: string;
  chain_sequence: number;
  reviewed: boolean;
  voided: boolean;
}

export interface ObservationVerifyResult {
  valid: boolean;
  computed_hash: string;
  stored_hash: string;
  chain_intact: boolean;
}

export interface ChainAuditResult {
  total_entries: number;
  broken_links: string[];
  chain_valid: boolean;
}

// ---------------------------------------------------------------------------
// Users + access grants
// ---------------------------------------------------------------------------

export interface User {
  id: UUID;
  name: string;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface UserRegister {
  name: string;
  email: string;
  password: string;
  role: UserRole;
}

export interface AccessGrant {
  id: UUID;
  user_id: UUID;
  scope_kind: AccessScopeKind;
  scope_stream: Stream | null;
  scope_owner_profile_id: UUID | null;
  scope_property_id: UUID | null;
  can_view_observations: boolean;
  can_view_chain_audit: boolean;
  can_view_financials: boolean;
  can_view_personal_data: boolean;
  granted_by: UUID;
  granted_at: string;
  expires_at: string | null;
}

// ---------------------------------------------------------------------------
// Activity dashboard
// ---------------------------------------------------------------------------

export interface PendingReviewItem {
  entry_id: UUID;
  entry_ref_id: string;
  submitted_at: string;
  property_name: string;
  building_label: string;
  zone_label: string;
  severity: Severity;
  observation_type: ObservationType;
  description_excerpt: string;
  intern_name: string;
  days_waiting: number;
}

export interface StaleZoneItem {
  zone_id: UUID;
  property_id: UUID;
  property_name: string;
  building_label: string;
  zone_label: string;
  owner_name: string;
  stream: Stream;
  last_submitted_at: string | null;
  days_stale: number | null;
  never_observed: boolean;
}

export interface WeeklyBucket {
  week_start: string; // ISO date "YYYY-MM-DD"
  normal: number;
  watch: number;
  alert: number;
  total: number;
}

export interface PhotoCoverage {
  total_alerts: number;
  alerts_with_photo: number;
  alert_coverage_pct: number;
  total_observations: number;
  observations_with_photo: number;
  overall_coverage_pct: number;
}

export interface ActivityResponse {
  pending_review: PendingReviewItem[];
  pending_review_total: number;
  stale_zones: StaleZoneItem[];
  stale_zones_total: number;
  stale_threshold_days: number;
  weekly_buckets: WeeklyBucket[];
  photo_coverage: PhotoCoverage;
  submissions_last_7_days: number;
}

// ---------------------------------------------------------------------------
// Analytics dashboard
// ---------------------------------------------------------------------------

export interface DashboardZoneRow {
  zone_id: UUID;
  property_id: UUID;
  owner_id: UUID;

  stream: Stream;
  owner_name: string;
  kyc_status: KycStatus;

  property_name: string;
  city: string | null;
  country: string | null;
  property_status: PropertyStatus;
  land_value: string | null;
  structure_value: string | null;

  building_label: string;
  zone_label: string;
  zone_active: boolean;

  total_observations: number;
  normal_count: number;
  watch_count: number;
  alert_count: number;
  reviewed_count: number;
  voided_count: number;

  last_submitted_at: string | null;
  last_severity: Severity | null;
  last_submitted_by_name: string | null;
  days_since_last: number | null;
}

export interface DashboardResponse {
  rows: DashboardZoneRow[];
  total_zones: number;
  total_properties: number;
  total_observations: number;
  total_zones_unfiltered: number;
  total_properties_unfiltered: number;
  total_observations_unfiltered: number;
}

export interface AccessGrantCreate {
  user_id: UUID;
  scope_kind: AccessScopeKind;
  scope_stream?: Stream;
  scope_owner_profile_id?: UUID;
  scope_property_id?: UUID;
  can_view_observations?: boolean;
  can_view_chain_audit?: boolean;
  can_view_financials?: boolean;
  can_view_personal_data?: boolean;
  expires_at?: string;
}
