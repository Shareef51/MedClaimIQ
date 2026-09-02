import { z } from "zod";

export const metricRecordSchema = z.record(z.string(), z.union([z.string(), z.number(), z.boolean(), z.null()]));
export const evidenceReferenceSchema = z.object({ type: z.string(), id: z.string() });
export type EvidenceReference = z.infer<typeof evidenceReferenceSchema>;

export const regulatoryExaminationCaseSchema = z.object({
  examination_case_id: z.string(), external_inquiry_reference: z.string(), status: z.string(), severity: z.string(),
  question_classification: z.string(), case_version: z.number(), response_due_at: z.string().nullable().optional(),
  open_document_requests: z.number().default(0), open_material_findings: z.number().default(0), open_commitments: z.number().default(0),
}).passthrough();
export const regulatoryExaminationDashboardSchema = z.object({
  kpis: metricRecordSchema.default({}), cases: z.array(regulatoryExaminationCaseSchema).default([]), authority: z.record(z.string(), z.unknown()).optional(),
}).passthrough();
export const regulatoryResponseSchema = z.object({
  response_id: z.string(), version: z.number(), status: z.string(), ai_assisted: z.boolean(), authority: z.string(), response_sha256: z.string(),
}).passthrough();
export const regulatoryFindingSchema = z.object({ finding_code: z.string(), material: z.boolean(), status: z.string(), description: z.string().optional() }).passthrough();
export const regulatoryCommitmentSchema = z.object({ commitment_key: z.string(), status: z.string(), due_at: z.string().nullable().optional(), evidence_refs: z.array(z.unknown()).default([]) }).passthrough();
export const regulatoryExaminationTraceSchema = z.object({
  case: regulatoryExaminationCaseSchema,
  evidence_packs: z.array(z.record(z.string(), z.unknown())).default([]),
  responses: z.array(regulatoryResponseSchema).default([]),
  findings: z.array(regulatoryFindingSchema).default([]),
  commitments: z.array(regulatoryCommitmentSchema).default([]),
}).passthrough();

export const remediationPlanSchema = z.object({
  plan_id: z.string(), finding_code: z.string(), plan_version: z.number(), status: z.string(), risk_level: z.string(), risk_score: z.number(),
  owner_user_id: z.string(), ai_authority: z.string(), due_at: z.string().nullable().optional(),
}).passthrough();
export const remediationDashboardSchema = z.object({ kpis: metricRecordSchema.default({}), plans: z.array(remediationPlanSchema).default([]) }).passthrough();
export const remediationTaskSchema = z.object({ task_key: z.string(), task_type: z.string(), status: z.string(), dependencies: z.array(z.string()).default([]) }).passthrough();
export const remediationRetestSchema = z.object({ control_key: z.string(), sequence: z.number(), outcome: z.string(), payload_sha256: z.string() }).passthrough();
export const remediationFollowupSchema = z.object({ followup_id: z.string(), version: z.number(), status: z.string(), response_sha256: z.string() }).passthrough();
export const remediationTraceSchema = z.object({
  plan: remediationPlanSchema, tasks: z.array(remediationTaskSchema).default([]), checkpoints: z.array(z.unknown()).default([]),
  retests: z.array(remediationRetestSchema).default([]), waivers: z.array(z.unknown()).default([]), followups: z.array(remediationFollowupSchema).default([]),
  certifications: z.array(z.unknown()).default([]),
}).passthrough();

export const supervisionAttestationSchema = z.object({ attestation_id: z.string(), control_effectiveness_pct: z.number(), material_blockers: z.array(z.unknown()).default([]) }).passthrough();
export const supervisionCaseSchema = z.object({
  case_id: z.string(), case_version: z.number(), status: z.string(), opened_reason: z.string(), acknowledgment_status: z.string().nullable().optional(),
  source_snapshot_sha256: z.string(), rejection_root_cause: z.string().nullable().optional(), amendment_effectiveness: z.string().nullable().optional(),
  latest_attestation: supervisionAttestationSchema.nullable().optional(),
}).passthrough();
export const supervisionDashboardSchema = z.object({
  kpis: metricRecordSchema.default({}), cases: z.array(supervisionCaseSchema).default([]),
  exceptions: z.array(z.object({ exception_id: z.string(), exception_code: z.string(), material: z.boolean(), status: z.string() }).passthrough()).default([]),
  deadlines: z.array(z.object({ deadline_id: z.string(), deadline_key: z.string(), due_date: z.string(), status: z.string() }).passthrough()).default([]),
}).passthrough();

export const portfolioControlSchema = z.object({ control_id: z.string(), control_key: z.string().optional(), name: z.string().optional(), family: z.string().optional(), version: z.number().optional() }).passthrough();
export const portfolioClusterSchema = z.object({
  cluster_key: z.string(), type: z.string(), severity: z.string(), member_count: z.number(),
  recommendation: z.object({ authority: z.string().optional() }).passthrough().nullable().optional(),
}).passthrough();
export const portfolioCriticalPathSchema = z.object({ plan_id: z.string(), task_key: z.string(), due_at: z.string(), dependency_count: z.number() }).passthrough();
export const portfolioSnapshotSchema = z.object({
  snapshot_id: z.string(), snapshot_version: z.number(), status: z.string(), metrics: metricRecordSchema.default({}), controls: z.array(portfolioControlSchema).default([]),
  clusters: z.array(portfolioClusterSchema).default([]), critical_path: z.array(portfolioCriticalPathSchema).default([]),
}).passthrough();
export const portfolioDashboardSchema = z.object({ latest: portfolioSnapshotSchema.nullable().optional() }).passthrough();
export const boardPackageSchema = z.object({ manifest_sha256: z.string() }).passthrough();


export const regulatoryTransportTransmissionSchema = z.object({
  transmission_id: z.string(), package_id: z.string(), destination_id: z.string(),
  supersedes_transmission_id: z.string().nullable().optional(), status: z.string(), attempt_count: z.number(),
  provider_message_id: z.string().nullable().optional(), external_submission_reference: z.string().nullable().optional(),
  envelope_sha256: z.string(), deadline_at: z.string().nullable().optional(), updated_at: z.string().nullable().optional(),
}).passthrough();
export const regulatoryTransportIncidentSchema = z.object({
  incident_id: z.string(), type: z.string(), status: z.string(), details: z.record(z.string(), z.unknown()).default({}),
}).passthrough();
export const regulatoryTransportDashboardSchema = z.object({
  authority: z.record(z.string(), z.unknown()).optional(), kpis: metricRecordSchema.default({}),
  transmissions: z.array(regulatoryTransportTransmissionSchema).default([]),
  incidents: z.array(regulatoryTransportIncidentSchema).default([]),
}).passthrough();
export const regulatoryTransportTraceSchema = z.object({
  transmission: regulatoryTransportTransmissionSchema, supersedes_transmission_id: z.string().nullable().optional(),
  delivery_attempts: z.array(z.record(z.string(), z.unknown())).default([]), release: z.record(z.string(), z.unknown()),
  package: z.record(z.string(), z.unknown()), certification: z.record(z.string(), z.unknown()),
  acknowledgments: z.array(z.record(z.string(), z.unknown())).default([]), audit_chain: z.array(z.record(z.string(), z.unknown())).default([]),
  provenance: z.string(), authority: z.record(z.string(), z.unknown()).optional(),
}).passthrough();

export const recoveryPortfolioSchema = z.object({
  cases: z.number(), open_cases: z.number(), identified_leakage: z.string(), verified_recovered: z.string(), recovery_rate_percent: z.number(), open_provider_disputes: z.number(),
}).passthrough();

export type RegulatoryExaminationCase = z.infer<typeof regulatoryExaminationCaseSchema>;
export type RegulatoryExaminationDashboard = z.infer<typeof regulatoryExaminationDashboardSchema>;
export type RegulatoryExaminationTrace = z.infer<typeof regulatoryExaminationTraceSchema>;
export type RegulatoryResponse = z.infer<typeof regulatoryResponseSchema>;
export type RegulatoryCommitment = z.infer<typeof regulatoryCommitmentSchema>;
export type RegulatoryFinding = z.infer<typeof regulatoryFindingSchema>;
export type RemediationPlan = z.infer<typeof remediationPlanSchema>;
export type RemediationDashboard = z.infer<typeof remediationDashboardSchema>;
export type RemediationTrace = z.infer<typeof remediationTraceSchema>;
export type RemediationTask = z.infer<typeof remediationTaskSchema>;
export type RemediationFollowup = z.infer<typeof remediationFollowupSchema>;
export type SupervisionCase = z.infer<typeof supervisionCaseSchema>;
export type SupervisionDashboard = z.infer<typeof supervisionDashboardSchema>;
export type PortfolioSnapshot = z.infer<typeof portfolioSnapshotSchema>;
export type PortfolioDashboard = z.infer<typeof portfolioDashboardSchema>;
export type RecoveryPortfolio = z.infer<typeof recoveryPortfolioSchema>;
export type RegulatoryTransportDashboard = z.infer<typeof regulatoryTransportDashboardSchema>;
export type RegulatoryTransportTransmission = z.infer<typeof regulatoryTransportTransmissionSchema>;
export type RegulatoryTransportTrace = z.infer<typeof regulatoryTransportTraceSchema>;
