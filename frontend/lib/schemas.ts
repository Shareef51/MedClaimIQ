import { z } from "zod";

export const reviewQueueItemSchema = z.object({
  work_item_id: z.string(),
  claim_id: z.string(),
  status: z.string(),
  priority_score: z.number(),
  priority_band: z.string(),
  priority_reasons: z.array(z.string()),
  assigned_reviewer_user_id: z.string().nullable(),
  sla_due_at: z.string().nullable()
});
export const reviewQueueSchema = z.array(reviewQueueItemSchema);

const evidenceItemSchema = z.object({
  evidence_id: z.string(), document_type: z.string(), media_type: z.string(), status: z.string(),
  source_type: z.string(), source_locator: z.string().nullable().optional(), content_sha256: z.string(),
  evidence_version: z.number(), authoritative: z.boolean()
});

const packItemSchema = z.object({
  evidence_key: z.string(), source_type: z.string(), source_id: z.string(), source_version: z.string().nullable().optional(),
  citation: z.record(z.string(), z.unknown()).or(z.unknown()), authority_rank: z.number(), confidence: z.number()
});

export const workbenchSchema = z.object({
  server_time: z.string(),
  claim: z.object({
    claim_id: z.string(), status: z.string(), status_version: z.number(), assigned_reviewer_user_id: z.string().nullable(),
    total_amount: z.string(), currency: z.string(), service_from: z.string().nullable().optional(), service_to: z.string().nullable().optional()
  }),
  evidence: z.array(evidenceItemSchema),
  evidence_lineage: z.array(z.object({ parent_evidence_id: z.string(), child_evidence_id: z.string(), relationship: z.string() })),
  evidence_pack: z.object({
    pack_id: z.string(), confidence: z.number(), coverage: z.number(), no_evidence: z.boolean(),
    items: z.array(packItemSchema),
    contradictions: z.array(z.object({ field_name: z.string(), severity: z.string(), status: z.string() }))
  }).nullable(),
  fhir_verifications: z.array(z.object({ verification_id: z.string(), status: z.string(), confidence: z.string(), findings: z.unknown() })),
  graph: z.object({
    edges: z.array(z.object({ source: z.string(), relationship: z.string(), target: z.string(), confidence: z.string() })),
    contradictions: z.array(z.object({ contradiction_id: z.string(), field_name: z.string(), severity: z.string(), status: z.string(), left_value: z.unknown(), right_value: z.unknown() }))
  }),
  agent_workflow: z.object({ workflow_id: z.string(), status: z.string(), selected_agents: z.array(z.string()), completed_agents: z.array(z.string()), failed_agents: z.array(z.string()) }).nullable(),
  agent_findings: z.array(z.object({ agent_name: z.string(), confidence: z.number(), evidence_keys: z.array(z.string()), risk_flags: z.array(z.string()), requires_human_review: z.boolean(), metadata: z.unknown() })),
  decision_support: z.object({ recommendation: z.string().nullable() }),
  guardrail: z.object({ run_id: z.string(), decision: z.string(), answerable: z.boolean(), evidence_quality: z.number(), unresolved_material_contradictions: z.number(), escalation_reasons: z.array(z.string()) }).nullable(),
  mcp_approvals: z.array(z.object({ approval_id: z.string(), tool_name: z.string(), status: z.string(), expires_at: z.string() })),
  sla: z.array(z.object({ timer_id: z.string(), timer_type: z.string(), status: z.string(), due_at: z.string(), seconds_remaining: z.number() })),
  review_notes: z.array(z.object({ note_id: z.string(), note_type: z.string(), body: z.string(), evidence_refs: z.array(z.string()), reviewer_user_id: z.string(), created_at: z.string() })),
  timeline: z.array(z.object({ at: z.string(), type: z.string(), summary: z.string(), actor_id: z.string().nullable().optional() }))
});

export const sessionSchema = z.object({
  user_id: z.string(), tenant_id: z.string(), role: z.string(), application_session_id: z.string().nullable(), token_issuer: z.string(), token_subject: z.string(), token_expires_at: z.string(), scopes: z.array(z.string())
});

export type ReviewQueueItem = z.infer<typeof reviewQueueItemSchema>;
export type Workbench = z.infer<typeof workbenchSchema>;
export type ReviewerSession = z.infer<typeof sessionSchema>;

export const portalClaimListItemSchema = z.object({
  claim_id:z.string(), external_claim_ref:z.string(), status:z.string(), total_amount:z.string(), currency:z.string(),
  service_from:z.string(), service_to:z.string().nullable(), outstanding_request_count:z.number(), next_deadline_at:z.string().nullable()
});
export const portalUploadTargetSchema=z.object({
  upload_session_id:z.string(),claim_id:z.string(),status:z.string(),method:z.string(),upload_url:z.string(),
  required_headers:z.record(z.string(),z.string()),form_fields:z.record(z.string(),z.string()),upload_expires_at:z.string(),expected_byte_size:z.number(),media_kind:z.string()
});
export const portalUploadInitiateSchema=z.object({submission_id:z.string(),acknowledgement_code:z.string(),upload:portalUploadTargetSchema});
export const portalUploadCompleteSchema=z.object({submission_id:z.string(),acknowledgement_code:z.string(),status:z.string(),accepted_for_security_processing:z.boolean(),event_id:z.string()});
export type PortalUploadInitiate=z.infer<typeof portalUploadInitiateSchema>;
export type PortalUploadComplete=z.infer<typeof portalUploadCompleteSchema>;

export const portalClaimListSchema=z.array(portalClaimListItemSchema);
export const portalClaimSchema=z.object({
  claim_id:z.string(), external_claim_ref:z.string(), status:z.string(), status_label:z.string(), total_amount:z.string(), currency:z.string(),
  service_from:z.string(), service_to:z.string().nullable(),
  document_requests:z.array(z.object({request_id:z.string(),requested_document_types:z.array(z.string()),instructions:z.string(),status:z.string(),due_at:z.string().nullable(),created_at:z.string()})),
  submissions:z.array(z.object({submission_id:z.string(),request_id:z.string(),document_type:z.string(),status:z.string(),acknowledgement_code:z.string(),upload_session_id:z.string(),evidence_id:z.string().nullable(),created_at:z.string(),received_at:z.string().nullable()})),
  verification:z.object({status:z.string(),confidence:z.string().nullable().optional(),message:z.string()}),
  deadlines:z.array(z.object({timer_type:z.string(),status:z.string(),due_at:z.string(),seconds_remaining:z.number()})),
  safe_timeline:z.array(z.object({at:z.string(),type:z.string(),summary:z.string()})), privacy_notice:z.string()
});
export type PortalClaimListItem=z.infer<typeof portalClaimListItemSchema>;
export type PortalClaim=z.infer<typeof portalClaimSchema>;

export const llmopsSloEventSchema=z.object({
  slo_event_id:z.string(), slo_kind:z.string(), observed_value:z.union([z.string(),z.number()]), threshold_value:z.union([z.string(),z.number()]), severity:z.string()
}).passthrough();
export type LLMOpsSloEvent=z.infer<typeof llmopsSloEventSchema>;

export const llmopsSummarySchema=z.object({
  window_minutes:z.number(),model_calls:z.number(),input_tokens:z.number(),output_tokens:z.number(),estimated_cost_usd:z.number().nullable(),unpriced_model_calls:z.number(),
  model_counts:z.record(z.string(),z.number()),model_latency_p95_ms:z.number(),agent_executions:z.number(),agent_error_rate:z.number(),agent_latency_p95_ms:z.number(),retrieval_runs:z.number(),retrieval_latency_p95_ms:z.number(),
  retrieval_no_evidence_rate:z.number(),mcp_invocations:z.number(),mcp_error_rate:z.number(),evaluation_runs:z.number(),evaluation_block_rate:z.number(),slo_events:z.array(llmopsSloEventSchema)
});
export type LLMOpsSummary=z.infer<typeof llmopsSummarySchema>;

const multimodalCitationSchema=z.record(z.string(),z.unknown());
export const multimodalReviewSchema=z.object({
  latest_pack:z.object({pack_id:z.string(),run_id:z.string(),pack_sha256:z.string(),modalities:z.array(z.string()),confidence:z.number(),modality_coverage:z.number(),citation_coverage:z.number(),answerability:z.string(),intent:z.string().nullable(),created_at:z.string()}).nullable(),
  items:z.array(z.object({item_id:z.string(),evidence_key:z.string(),modality:z.string(),domain:z.string(),source_id:z.string(),source_version:z.string(),content_sha256:z.string(),rank:z.number(),score:z.number(),confidence:z.number(),authority_rank:z.number(),citation:multimodalCitationSchema,metadata:z.record(z.string(),z.unknown()),retrieval_sources:z.array(z.string()),evidence_id:z.string().nullable().optional(),media_type:z.string().nullable().optional(),document_type:z.string().nullable().optional(),display_text:z.string().nullable().optional(),structured_data:z.record(z.string(),z.unknown()).optional(),fhir_resource:z.object({canonical_resource:z.record(z.string(),z.unknown()).optional()}).passthrough().nullable().optional()})),
  inconsistencies:z.array(z.object({inconsistency_id:z.string(),code:z.string(),field:z.string(),severity:z.string(),left_item_id:z.string(),right_item_id:z.string(),confidence:z.number(),human_review_required:z.boolean(),created_at:z.string()})),
  investigations:z.array(z.object({investigation_id:z.string(),agent_name:z.string(),attempt:z.number(),pack_id:z.string(),pack_sha256:z.string(),answerability:z.string(),confidence:z.number(),requested_modalities:z.array(z.string()),required_modalities:z.array(z.string()),material_inconsistency_count:z.number(),blocking_gap_count:z.number(),human_review_required:z.boolean(),escalation_reasons:z.array(z.string()),trace_id:z.string().nullable(),created_at:z.string()})),
  agent_findings:z.array(z.object({finding_id:z.string(),agent_name:z.string(),confidence:z.number(),requires_human_review:z.boolean(),risk_flags:z.array(z.string()),evidence_keys:z.array(z.string()),multimodal_evidence:z.array(z.object({item_id:z.string(),evidence_key:z.string(),citation:multimodalCitationSchema}).passthrough()),metadata:z.record(z.string(),z.unknown()),created_at:z.string()})),
  checkpoint:z.object({checkpoint_id:z.string(),workflow_id:z.string(),reason:z.string(),status:z.string(),required_permissions:z.array(z.string()),metadata:z.record(z.string(),z.unknown()),created_at:z.string(),resumed_at:z.string().nullable()}).nullable(),
  annotations:z.array(z.object({annotation_id:z.string(),reviewer_user_id:z.string(),target_type:z.string(),target_id:z.string(),annotation_kind:z.string(),anchor:z.record(z.string(),z.unknown()),body:z.string(),tags:z.array(z.string()),created_at:z.string()})),
  traceability:z.object({multimodal_item_count:z.number(),investigation_count:z.number(),finding_count:z.number(),annotation_count:z.number(),final_decision_human_only:z.boolean()})
});
export type MultimodalReview=z.infer<typeof multimodalReviewSchema>;

export const governedDecisionPacketSchema=z.object({
  packet_id:z.string(),claim_id:z.string(),primary_reviewer_user_id:z.string(),packet_version:z.number(),decision:z.string(),rationale:z.string(),reason_codes:z.array(z.string()),
  approved_amount:z.string().or(z.number()).nullable().optional(),denied_amount:z.string().or(z.number()).nullable().optional(),partial_line_decisions:z.array(z.unknown()),
  evidence_snapshot:z.array(z.unknown()),evidence_snapshot_sha256:z.string(),finding_refs:z.array(z.string()),annotation_refs:z.array(z.string()),inconsistency_refs:z.array(z.string()),checkpoint_refs:z.array(z.string()),
  ai_recommendation:z.string().nullable(),ai_disagreement:z.boolean(),ai_disagreement_reason:z.string().nullable(),escalation_queue:z.string().nullable(),dual_control_required:z.boolean(),expected_claim_status_version:z.number(),
  status:z.string(),blocker_codes:z.array(z.string()),completeness:z.record(z.string(),z.unknown()),second_reviewer_user_id:z.string().nullable(),decision_id:z.string().nullable(),created_at:z.string(),updated_at:z.string(),locked_at:z.string().nullable(),closed_at:z.string().nullable(),locked_payload_sha256:z.string().nullable()
});
export const governedClosureSchema=z.object({
  claim:z.object({claim_id:z.string(),status:z.string(),status_version:z.number(),total_amount:z.string(),currency:z.string()}),
  decision_packet:governedDecisionPacketSchema.nullable(),validation:z.object({blockers:z.array(z.string()),details:z.record(z.string(),z.unknown()),claim_status_version:z.number()}).nullable(),
  second_reviews:z.array(z.object({second_review_id:z.string(),reviewer_user_id:z.string(),action:z.string(),rationale:z.string(),packet_version:z.number(),payload_sha256:z.string(),created_at:z.string()})),
  audit_chain:z.array(z.object({audit_event_id:z.string(),sequence:z.number(),event_type:z.string(),actor_type:z.string(),actor_id:z.string(),previous_event_sha256:z.string().nullable(),event_sha256:z.string(),occurred_at:z.string()})),
  notifications:z.array(z.object({notification_id:z.string(),audience:z.string(),notification_type:z.string(),status:z.string(),created_at:z.string()})),
  human_authority:z.object({final_claim_decision_requires_authenticated_reviewer:z.boolean(),llm_can_adjudicate:z.boolean(),langgraph_can_adjudicate:z.boolean(),rag_can_adjudicate:z.boolean(),mcp_can_adjudicate:z.boolean(),automated_financial_execution:z.boolean()})
});
export type GovernedDecisionPacket=z.infer<typeof governedDecisionPacketSchema>;
export type GovernedClosure=z.infer<typeof governedClosureSchema>;

export const postDecisionSchema=z.object({
  claim_id:z.string(),
  notices:z.array(z.object({
    notice_id:z.string(),packet_id:z.string(),decision_id:z.string(),appeal_id:z.string().nullable(),resolution_id:z.string().nullable(),
    template_key:z.string(),template_version:z.string(),notice_version:z.number(),audience:z.string(),status:z.string(),reason_explanations:z.array(z.unknown()),
    rendered_payload_sha256:z.string(),evidence_snapshot_sha256:z.string(),released_by_user_id:z.string().nullable(),released_at:z.string().nullable(),
    notification_id:z.string().nullable(),delivery_status:z.string().nullable(),delivery_attempts:z.number(),created_at:z.string()
  })),
  appeals:z.array(z.object({
    appeal_id:z.string(),notice_id:z.string(),status:z.string(),grounds:z.array(z.string()),statement:z.string(),late_filing_reason:z.string().nullable(),
    appeal_due_at:z.string(),submitted_at:z.string(),assigned_reviewer_user_id:z.string().nullable(),appeal_version:z.number(),reopened_at:z.string().nullable(),resolved_at:z.string().nullable(),
    supplemental_evidence:z.array(z.object({evidence_id:z.string(),evidence_version:z.number(),content_sha256:z.string(),linked_at:z.string()})),
    resolution:z.object({resolution_id:z.string(),reviewer_user_id:z.string(),outcome:z.string(),controlling_decision:z.string(),reason_codes:z.array(z.string()),payload_sha256:z.string(),resolved_at:z.string()}).nullable()
  })),
  decision_history:z.array(z.object({history_version_id:z.string(),sequence:z.number(),source_type:z.string(),source_id:z.string(),decision:z.string(),human_reviewer_user_id:z.string(),evidence_snapshot_sha256:z.string(),previous_version_sha256:z.string().nullable(),version_sha256:z.string(),effective_at:z.string()})),
  correspondence:z.array(z.object({correspondence_id:z.string(),appeal_id:z.string().nullable(),notice_id:z.string().nullable(),direction:z.string(),channel:z.string(),audience:z.string(),external_message_id:z.string().nullable(),payload_sha256:z.string(),actor_type:z.string(),actor_id:z.string(),occurred_at:z.string()})),
  tasks:z.array(z.object({task_id:z.string(),claim_id:z.string(),appeal_id:z.string().nullable(),notice_id:z.string().nullable(),task_type:z.string(),priority:z.number(),assigned_reviewer_user_id:z.string().nullable(),due_at:z.string(),sla_breached:z.boolean()})),
  traceability:z.object({claim_id:z.string(),nodes:z.array(z.unknown()),edges:z.array(z.unknown()),original_evidence_to_original_decision_to_appeal_evidence_to_reconsideration:z.boolean(),original_decision_immutable:z.boolean(),final_resolution_human_only:z.boolean()}),
  human_authority:z.object({ai_can_draft:z.boolean(),llm_can_issue_or_overturn:z.boolean(),langgraph_can_issue_or_overturn:z.boolean(),rag_can_issue_or_overturn:z.boolean(),mcp_can_issue_or_overturn:z.boolean(),automated_financial_execution:z.boolean()})
});
export type PostDecision=z.infer<typeof postDecisionSchema>;

const decisionReasonExplanationSchema=z.object({reason_code:z.string(),explanation:z.string()}).passthrough();
const portalAppealEvidenceSchema=z.object({evidence_id:z.string(),evidence_version:z.number().optional(),content_sha256:z.string().optional(),linked_at:z.string().optional()}).passthrough();
const portalAppealResolutionSchema=z.object({resolution_id:z.string(),reviewer_user_id:z.string(),outcome:z.string(),controlling_decision:z.string(),reason_codes:z.array(z.string()),payload_sha256:z.string(),resolved_at:z.string()}).passthrough();
export const portalPostDecisionSchema=z.object({
  claim_id:z.string(),appeal_window_days:z.number(),
  notices:z.array(z.object({notice_id:z.string(),packet_id:z.string(),decision_id:z.string(),appeal_id:z.string().nullable(),resolution_id:z.string().nullable(),template_key:z.string(),template_version:z.string(),notice_version:z.number(),audience:z.string(),status:z.string(),reason_explanations:z.array(decisionReasonExplanationSchema),rendered_payload_sha256:z.string(),evidence_snapshot_sha256:z.string(),released_by_user_id:z.string().nullable(),released_at:z.string().nullable(),notification_id:z.string().nullable(),delivery_status:z.string().nullable(),delivery_attempts:z.number(),created_at:z.string()})),
  appeals:z.array(z.object({appeal_id:z.string(),notice_id:z.string(),status:z.string(),grounds:z.array(z.string()),late_filing_reason:z.string().nullable(),appeal_due_at:z.string(),submitted_at:z.string(),assigned_reviewer_user_id:z.string().nullable(),appeal_version:z.number(),reopened_at:z.string().nullable(),resolved_at:z.string().nullable(),supplemental_evidence:z.array(portalAppealEvidenceSchema),resolution:portalAppealResolutionSchema.nullable()})),
  human_authority:z.object({ai_can_issue_or_overturn:z.boolean(),appeal_resolution_requires_independent_human:z.boolean()})
});
export type PortalPostDecision=z.infer<typeof portalPostDecisionSchema>;

export const appealReconsiderationSchema=z.object({
  claim_id:z.string(),appeal_id:z.string(),appeal_status:z.string(),assigned_reviewer_user_id:z.string().nullable(),appeal_version:z.number(),
  evidence_snapshot:z.object({snapshot_id:z.string(),snapshot_version:z.number(),status:z.string(),snapshot_sha256:z.string(),original_evidence_snapshot_sha256:z.string(),original_sources:z.array(z.unknown()),supplemental_sources:z.array(z.unknown()),modalities:z.array(z.string()),source_count:z.number(),locked_at:z.string().or(z.date()).nullable()}).nullable(),
  reingestions:z.array(z.object({reingestion_id:z.string(),source_kind:z.string(),source_id:z.string(),source_version:z.string(),modality:z.string(),media_type:z.string().nullable(),file_validation_status:z.string(),malware_verdict:z.string(),extraction_status:z.string(),chunk_count:z.number(),embedding_model:z.string(),embedding_dimensions:z.number(),index_version:z.string(),status:z.string(),error_code:z.string().nullable()})),
  comparisons:z.array(z.object({comparison_id:z.string(),comparison_type:z.string(),field:z.string(),severity:z.string(),confidence:z.number(),description:z.string(),original_source_ref:z.string().nullable(),supplemental_source_ref:z.string().nullable(),citations:z.array(z.unknown())})),
  latest_rag:z.object({run_id:z.string(),snapshot_id:z.string(),strategy:z.string(),selected_count:z.number(),citation_coverage:z.number(),contradiction_count:z.number(),changed_fact_count:z.number(),pack_sha256:z.string(),items:z.array(z.object({item_id:z.string(),source_scope:z.string().optional(),source_version:z.string().optional(),score:z.number().optional(),text_preview:z.string().optional(),citation:z.record(z.string(),z.unknown()).optional()}).passthrough())}).nullable(),
  recommendations:z.array(z.object({reconsideration_run_id:z.string(),rag_run_id:z.string(),graph_thread_id:z.string(),agent_name:z.string(),recommendation:z.string(),confidence:z.number(),recommendation_summary:z.string(),recommendation_sha256:z.string(),evidence_refs:z.array(z.unknown()),changed_fact_refs:z.array(z.unknown()),contradiction_refs:z.array(z.unknown()),missing_evidence_requests:z.array(z.unknown()),escalation_reasons:z.array(z.unknown()),requires_human_review:z.boolean(),adjudication_authority:z.string(),created_at:z.string().or(z.date())})),
  checkpoints:z.array(z.object({checkpoint_id:z.string(),thread_id:z.string(),checkpoint_version:z.number(),stage:z.string(),status:z.string(),state_sha256:z.string(),requires_human_action:z.boolean(),created_at:z.string().or(z.date()),resumed_by_user_id:z.string().nullable(),resumed_at:z.string().or(z.date()).nullable()})),
  annotations:z.array(z.object({annotation_id:z.string()}).passthrough()),missing_evidence_requests:z.array(z.unknown()),escalations:z.array(z.unknown()),traceability:z.unknown(),
  human_authority:z.object({recommendation_only:z.boolean(),llm_can_affirm_modify_or_overturn:z.boolean(),langgraph_can_affirm_modify_or_overturn:z.boolean(),rag_can_affirm_modify_or_overturn:z.boolean(),mcp_can_affirm_modify_or_overturn:z.boolean(),independent_human_required:z.boolean()})
});
export type AppealReconsideration=z.infer<typeof appealReconsiderationSchema>;

export const appealResolutionSchema=z.object({
  claim_id:z.string(),appeal_id:z.string(),appeal_status:z.string(),appeal_version:z.number(),
  packet:z.object({packet_id:z.string(),status:z.string(),packet_version:z.number(),primary_reviewer_user_id:z.string(),second_reviewer_user_id:z.string().nullable(),snapshot_id:z.string(),snapshot_sha256:z.string(),recommendation_run_id:z.string().nullable(),outcome:z.string(),controlling_decision:z.string(),rationale:z.string(),reason_codes:z.array(z.string()),citation_refs:z.array(z.string()),resolved_comparison_refs:z.array(z.string()),original_approved_amount:z.string(),reconsidered_approved_amount:z.string(),financial_delta:z.string(),material_financial_change:z.boolean(),recommendation_disagreement:z.boolean(),recommendation_disagreement_reason:z.string().nullable(),completeness:z.unknown(),blocker_codes:z.array(z.string()),dual_control_required:z.boolean(),locked_payload_sha256:z.string().nullable(),final_resolution_id:z.string().nullable()}).nullable(),
  second_reviews:z.array(z.unknown()),final_resolution:z.unknown().nullable(),supersession_chain:z.array(z.unknown()),audit_chain:z.array(z.unknown()),authority:z.object({llm:z.boolean(),langgraph:z.boolean(),rag:z.boolean(),mcp:z.boolean(),automation:z.boolean(),authorized_human_reviewers_required:z.boolean()})
});
export type AppealResolution=z.infer<typeof appealResolutionSchema>;


export const financialPacketSchema=z.object({
  packet_id:z.string(),packet_version:z.number(),status:z.string(),controlling_source_type:z.string(),controlling_source_id:z.string(),decision_history_version_id:z.string(),decision_history_sha256:z.string(),evidence_snapshot_sha256:z.string(),controlling_decision:z.string(),claim_total_amount:z.string(),approved_amount:z.string(),payer_responsibility:z.string(),member_responsibility:z.string(),currency:z.string(),line_reconciliation:z.unknown(),prepared_by_user_id:z.string(),authorized_by_user_id:z.string().nullable(),locked_payload_sha256:z.string().nullable(),authorized_payload_sha256:z.string().nullable()
});
const remittanceArtifactSchema=z.object({artifact_id:z.string(),artifact_type:z.string(),format_version:z.string(),content_sha256:z.string(),content:z.unknown()});
const financialHoldSchema=z.object({hold_id:z.string(),hold_type:z.string(),reason_code:z.string(),rationale:z.string(),active:z.boolean()});
const paymentIntentSchema=z.object({payment_intent_id:z.string(),packet_id:z.string().optional(),amount:z.string(),currency:z.string(),payee_ref:z.string(),status:z.string(),external_instruction_id:z.string().nullable().optional(),payment_fingerprint:z.string().optional()});
const settlementEventSchema=z.object({settlement_event_id:z.string(),payment_intent_id:z.string(),provider_event_id:z.string().nullable().optional(),status:z.string(),settled_amount:z.string().nullable(),currency:z.string(),external_reference:z.string().nullable().optional()});
const reconciliationExceptionSchema=z.object({exception_id:z.string(),payment_intent_id:z.string().nullable().optional(),exception_type:z.string(),expected:z.unknown().optional(),observed:z.unknown().optional(),status:z.string()});
const operationsTaskSchema=z.object({task_id:z.string(),task_type:z.string(),status:z.string(),priority:z.number().optional(),due_at:z.union([z.string(),z.date()]).optional(),sla_breached:z.boolean().optional()});
const auditEventSchema=z.object({sequence:z.number(),event_type:z.string(),actor_type:z.string(),actor_id:z.string(),event_sha256:z.string(),previous_event_sha256:z.string().nullable().optional(),occurred_at:z.union([z.string(),z.date()]).optional()});
export const financialHandoffSchema=z.object({
  claim_id:z.string(),authority:z.object({llm_can_authorize_funds:z.boolean(),langgraph_can_authorize_funds:z.boolean(),rag_can_authorize_funds:z.boolean(),mcp_can_authorize_funds:z.boolean(),background_worker_can_authorize_funds:z.boolean(),adapter_can_authorize_funds:z.boolean(),authorized_human_finance_approver_required:z.boolean(),segregation_of_duties_required:z.boolean(),automatic_fund_movement:z.boolean()}),
  packet:financialPacketSchema.nullable(),remittance_artifacts:z.array(remittanceArtifactSchema),active_holds:z.array(financialHoldSchema),payment_intents:z.array(paymentIntentSchema),settlements:z.array(settlementEventSchema),exceptions:z.array(reconciliationExceptionSchema),tasks:z.array(operationsTaskSchema),audit:z.array(auditEventSchema),traceability:z.unknown().optional()
});
export type FinancialHandoff=z.infer<typeof financialHandoffSchema>;
export type FinancialPacket=z.infer<typeof financialPacketSchema>;

const accountingReconciliationSchema=z.object({reconciliation_id:z.string(),payment_intent_id:z.string(),expected_amount:z.string(),era_total:z.string(),eft_total:z.string(),matched_amount:z.string(),unmatched_amount:z.string(),reference_match:z.boolean(),status:z.string(),reconciliation_sha256:z.string(),journal_id:z.string().nullable()});
const ledgerEntrySchema=z.object({entry_id:z.string(),sequence:z.number(),account_code:z.string(),direction:z.string(),amount:z.string(),currency:z.string(),memo:z.string().nullable().optional()});
const ledgerJournalSchema=z.object({journal_id:z.string(),period_id:z.string(),journal_type:z.string(),source_type:z.string(),source_id:z.string(),currency:z.string(),total_debits:z.string(),total_credits:z.string(),previous_journal_sha256:z.string().nullable(),journal_sha256:z.string(),posted_by_actor_type:z.string(),posted_by_actor_id:z.string(),entries:z.array(ledgerEntrySchema)});
const paymentReturnSchema=z.object({return_id:z.string(),payment_intent_id:z.string(),return_reference:z.string().nullable().optional(),return_code:z.string(),amount:z.string(),status:z.string(),journal_id:z.string().nullable()});
const accountingAdjustmentSchema=z.object({adjustment_id:z.string(),payment_intent_id:z.string(),adjustment_type:z.string(),amount:z.string(),status:z.string(),requested_by_user_id:z.string(),approved_by_user_id:z.string().nullable(),journal_id:z.string().nullable()});
const providerRemittanceSchema=z.object({payment_intent_id:z.string(),provider_ref:z.string(),status:z.string(),remitted_amount:z.string(),latest_era_reference:z.string().nullable(),latest_eft_reference:z.string().nullable()});
const accountingAgingSchema=z.object({queue_id:z.string(),payment_intent_id:z.string(),status:z.string(),age_days:z.number(),aging_bucket:z.string(),priority:z.number(),exception_codes:z.array(z.string())});
const accountingPeriodSchema=z.object({period_id:z.string(),period_key:z.string(),status:z.string(),lock_version:z.number(),close_summary:z.unknown().nullable().optional(),close_sha256:z.string().nullable(),closed_by_user_id:z.string().nullable()});
export const accountingLedgerSchema=z.object({
  claim_id:z.string(),authority:z.object({llm_can_post_journal:z.boolean(),langgraph_can_post_journal:z.boolean(),rag_can_post_journal:z.boolean(),mcp_can_post_journal:z.boolean(),background_worker_can_post_journal:z.boolean(),background_worker_can_close_period:z.boolean(),ai_can_authorize_adjustment_or_recoupment:z.boolean(),automatic_fund_movement:z.boolean(),human_finance_approval_required:z.boolean(),human_accounting_controller_close_required:z.boolean(),double_entry_required:z.boolean()}),
  payment_intents:z.array(paymentIntentSchema),reconciliations:z.array(accountingReconciliationSchema),journals:z.array(ledgerJournalSchema),returns:z.array(paymentReturnSchema),adjustments:z.array(accountingAdjustmentSchema),provider_remittance:z.array(providerRemittanceSchema),aging_queue:z.array(accountingAgingSchema),periods:z.array(accountingPeriodSchema),traceability:z.unknown()
});
export type AccountingLedger=z.infer<typeof accountingLedgerSchema>;

const financialCitationSchema=z.object({citation_id:z.string(),type:z.string(),sha256:z.string().nullable().optional(),status:z.string().optional(),claim_id:z.string().optional(),retrieval_score:z.number().optional()}).passthrough();
const anomalyFactorSchema=z.object({factor:z.string(),points:z.number(),detail:z.unknown()});
const reserveHistorySchema=z.object({reserve_snapshot_id:z.string(),outstanding_reserve:z.string(),reserve_variance:z.string(),adequacy_score:z.number(),created_at:z.string()});
const financialMetricsSchema=z.object({approved_incurred:z.string(),net_paid:z.string(),outstanding_reserve:z.string(),reserve_variance:z.string(),reserve_adequacy_score:z.number(),financial_leakage_exposure:z.string(),reconciliation_anomaly_score:z.number(),max_reconciliation_age_days:z.number()}).passthrough();
export const financialIntelligenceClaimSchema=z.object({claim_id:z.string(),authority:z.record(z.string(),z.unknown()),metrics:financialMetricsSchema,anomaly_factors:z.array(anomalyFactorSchema),citations:z.array(financialCitationSchema),source_watermark_sha256:z.string(),reserve_history:z.array(reserveHistorySchema)});
export type FinancialIntelligenceClaim=z.infer<typeof financialIntelligenceClaimSchema>;
const providerPatternSchema=z.object({provider_ref:z.string(),pattern_risk_score:z.number(),remitted_total:z.string(),returned_amount:z.string(),open_exception_count:z.number(),recoupment_amount:z.string()}).passthrough();
const recoupmentAgingSchema=z.object({adjustment_id:z.string(),claim_id:z.string(),amount:z.string(),age_days:z.number(),status:z.string()}).passthrough();
const closeBlockerSchema=z.object({code:z.string(),count:z.number()}).passthrough();
const periodCloseReadinessSchema=z.object({period_id:z.string(),period_key:z.string(),status:z.string(),readiness_score:z.number(),blockers:z.array(closeBlockerSchema)}).passthrough();
const accountingControlExceptionSchema=z.object({period_id:z.string(),period_key:z.string(),code:z.string(),count:z.number(),weight:z.number()}).passthrough();
const financialPortfolioKpisSchema=z.object({claims_analyzed:z.number(),incurred_amount:z.string(),net_paid_amount:z.string(),outstanding_reserve:z.string(),financial_leakage_exposure:z.string(),high_risk_claims:z.number(),open_recoupments:z.number(),period_close_readiness_average:z.number()}).passthrough();
export const financialIntelligencePortfolioSchema=z.object({authority:z.record(z.string(),z.unknown()),kpis:financialPortfolioKpisSchema,claims:z.array(z.record(z.string(),z.unknown())),provider_patterns:z.array(providerPatternSchema),recoupment_aging:z.array(recoupmentAgingSchema),accounting_control_exceptions:z.array(accountingControlExceptionSchema),period_close_readiness:z.array(periodCloseReadinessSchema),anomalies:z.array(z.record(z.string(),z.unknown())),source_watermark_sha256:z.string()});
export type FinancialIntelligencePortfolio=z.infer<typeof financialIntelligencePortfolioSchema>;
export type FinancialCitation=z.infer<typeof financialCitationSchema>;
export type FinancialAnomalyFactor=z.infer<typeof anomalyFactorSchema>;

const financialInvestigationCaseSchema=z.object({case_id:z.string(),claim_id:z.string(),source_investigation_id:z.string(),anomaly_code:z.string(),anomaly_score:z.number(),severity:z.string(),case_type:z.string(),cluster_key:z.string().nullable().optional(),provider_organization_id:z.string().nullable().optional(),status:z.string(),priority:z.number(),assigned_investigator_user_id:z.string().nullable(),root_cause_code:z.string().nullable(),root_cause_rationale:z.string().nullable(),ai_recommendation:z.object({recommended_root_cause:z.string().nullable().optional()}).passthrough(),ai_disagreement_rationale:z.string().nullable(),case_version:z.number(),created_at:z.union([z.string(),z.date()]),updated_at:z.union([z.string(),z.date()]),closed_at:z.union([z.string(),z.date()]).nullable(),closure_reason_code:z.string().nullable(),closure_rationale:z.string().nullable()});
const financialInvestigationQueueItemSchema=financialInvestigationCaseSchema.extend({sla_breached:z.boolean()});
const investigationEvidenceItemSchema=z.object({type:z.string(),id:z.string()}).passthrough();
const investigationEvidencePackSchema=z.object({evidence_pack_id:z.string(),pack_version:z.number(),source_watermark_sha256:z.string(),evidence_items:z.array(investigationEvidenceItemSchema),citations:z.array(financialCitationSchema),related_case_ids:z.array(z.string()),payload_sha256:z.string()});
const remediationProposalSchema=z.object({proposal_id:z.string(),remediation_type:z.string(),amount:z.string(),currency:z.string(),reason_code:z.string(),rationale:z.string(),evidence_pack_sha256:z.string(),root_cause_code:z.string(),material:z.boolean(),status:z.string(),proposed_by_user_id:z.string(),approved_by_user_id:z.string().nullable(),approval_rationale:z.string().nullable(),referral_type:z.string().nullable(),referral_id:z.string().nullable(),payload_sha256:z.string()});
const investigationAnnotationSchema=z.object({annotation_id:z.string(),reviewer_user_id:z.string(),target_type:z.string(),target_id:z.string(),body:z.string(),tags:z.array(z.string()),body_sha256:z.string(),created_at:z.union([z.string(),z.date()])});
export const financialInvestigationQueueSchema=z.array(financialInvestigationQueueItemSchema);
export const financialInvestigationWorkbenchSchema=z.object({case:financialInvestigationCaseSchema,evidence_pack:investigationEvidencePackSchema.nullable(),lease:z.object({investigator_user_id:z.string(),lease_version:z.number(),expires_at:z.union([z.string(),z.date()])}).nullable(),cluster:z.array(financialInvestigationCaseSchema),annotations:z.array(investigationAnnotationSchema),remediation_proposals:z.array(remediationProposalSchema),tasks:z.array(operationsTaskSchema),audit_chain:z.array(auditEventSchema),authority:z.record(z.string(),z.unknown())});
export type FinancialInvestigationQueue=z.infer<typeof financialInvestigationQueueSchema>;
export type FinancialInvestigationQueueItem=z.infer<typeof financialInvestigationQueueItemSchema>;
export type FinancialInvestigationWorkbench=z.infer<typeof financialInvestigationWorkbenchSchema>;

const recoveryCaseSchema=z.object({recovery_case_id:z.string(),claim_id:z.string(),financial_investigation_case_id:z.string(),source_proposal_id:z.string(),referral_type:z.string(),referral_id:z.string(),recovery_type:z.string(),provider_organization_id:z.string().nullable(),currency:z.string(),identified_amount:z.string(),target_recovery_amount:z.string(),recovered_amount:z.string(),status:z.string(),priority:z.number(),assigned_investigator_user_id:z.string().nullable(),case_version:z.number(),effectiveness_score:z.number(),last_verified_at:z.union([z.string(),z.date()]).nullable(),created_at:z.union([z.string(),z.date()]),updated_at:z.union([z.string(),z.date()]),closed_at:z.union([z.string(),z.date()]).nullable(),closure_reason_code:z.string().nullable(),closure_rationale:z.string().nullable()});
const recoveryQueueItemSchema=recoveryCaseSchema.extend({sla_breached:z.boolean(),open_disputes:z.number()});
const recoveryCitationSchema=z.object({type:z.string(),id:z.string()}).passthrough();
const recoveryEvidencePackSchema=z.object({evidence_pack_id:z.string(),pack_version:z.number(),evidence_items:z.array(z.unknown()),citations:z.array(recoveryCitationSchema),source_sha256:z.string(),payload_sha256:z.string()});
const recoveryOutcomeSchema=z.object({outcome_id:z.string(),outcome_type:z.string(),source_type:z.string(),source_id:z.string(),amount:z.string(),currency:z.string(),status:z.string(),external_reference:z.string().nullable(),details:z.unknown(),payload_sha256:z.string(),occurred_at:z.union([z.string(),z.date()])});
const recoveryDisputeSchema=z.object({dispute_id:z.string(),external_reference:z.string(),disputed_amount:z.string(),currency:z.string(),reason_code:z.string(),evidence_refs:z.array(z.unknown()),evidence_pack_sha256:z.string(),material:z.boolean(),status:z.string(),submitted_by_user_id:z.string(),assigned_resolver_user_id:z.string().nullable(),resolution_outcome:z.string().nullable(),resolution_rationale:z.string().nullable(),resolution_amount:z.string().nullable(),payload_sha256:z.string(),submitted_at:z.union([z.string(),z.date()]),resolved_at:z.union([z.string(),z.date()]).nullable()});
export const recoveryOperationsQueueSchema=z.array(recoveryQueueItemSchema);
export const recoveryOperationsWorkbenchSchema=z.object({case:recoveryCaseSchema,evidence_pack:recoveryEvidencePackSchema.nullable(),lease:z.object({investigator_user_id:z.string(),lease_version:z.number(),expires_at:z.union([z.string(),z.date()])}).nullable(),downstream_state:z.object({source_type:z.string(),status:z.string()}).passthrough(),outcomes:z.array(recoveryOutcomeSchema),disputes:z.array(recoveryDisputeSchema),correspondence:z.array(z.record(z.string(),z.unknown())),tasks:z.array(operationsTaskSchema),aging:z.object({age_days:z.number(),bucket:z.string()}),effectiveness:z.object({identified_amount:z.string(),recovered_amount:z.string(),recovered_vs_identified_percent:z.number(),score:z.number()}),audit_chain:z.array(auditEventSchema),authority:z.record(z.string(),z.unknown())});
export const recoveryOperationsPortfolioSchema=z.object({cases:z.number(),open_cases:z.number(),identified_leakage:z.string(),verified_recovered:z.string(),recovery_rate_percent:z.number(),open_provider_disputes:z.number(),authority:z.string()});
export type RecoveryOperationsQueue=z.infer<typeof recoveryOperationsQueueSchema>;
export type RecoveryQueueItem=z.infer<typeof recoveryQueueItemSchema>;
export type RecoveryOperationsWorkbench=z.infer<typeof recoveryOperationsWorkbenchSchema>;
export type RecoveryOperationsPortfolio=z.infer<typeof recoveryOperationsPortfolioSchema>;

const providerDisputeQueueItemSchema=z.object({recovery_case_id:z.string(),dispute_id:z.string(),external_reference:z.string(),provider_organization_id:z.string().nullable(),disputed_amount:z.string(),currency:z.string(),reason_code:z.string(),status:z.string(),material:z.boolean(),submitted_at:z.union([z.string(),z.date()]),evidence_sources:z.number(),recommendation_runs:z.number(),open_missing_evidence:z.number()});
const providerPolicySourceSchema=z.object({source_id:z.string(),title:z.string(),source_kind:z.string(),source_version:z.string(),effective_from:z.string().nullable().optional(),content_sha256:z.string()}).passthrough();
const providerSnapshotSchema=z.object({snapshot_id:z.string(),snapshot_version:z.number(),snapshot_sha256:z.string(),recovery_evidence_pack_sha256:z.string(),provider_sources:z.array(z.unknown()),policy_sources:z.array(providerPolicySourceSchema),modalities:z.array(z.string()),source_count:z.number(),status:z.string(),locked_at:z.union([z.string(),z.date()])});
const providerReingestionSchema=z.object({reingestion_id:z.string(),source_kind:z.string(),source_id:z.string(),source_version:z.string(),modality:z.string(),media_type:z.string().nullable(),content_sha256:z.string(),file_validation_status:z.string(),malware_verdict:z.string(),extraction_status:z.string(),chunk_count:z.number(),status:z.string(),error_code:z.string().nullable()});
const providerComparisonSchema=z.object({comparison_id:z.string(),comparison_type:z.string(),field:z.string(),severity:z.string(),confidence:z.number(),description:z.string(),recovery_source_ref:z.string().nullable(),provider_source_ref:z.string().nullable(),citations:z.array(z.unknown())});
export const evidenceSearchItemSchema=z.object({item_id:z.string(),source_scope:z.string(),source_id:z.string(),source_version:z.string(),modality:z.string(),rank:z.number(),score:z.number(),content_sha256:z.string(),text_preview:z.string(),citation:z.record(z.string(),z.unknown())});
export const evidenceSearchResultSchema=z.object({items:z.array(evidenceSearchItemSchema)}).passthrough();
const providerRecommendationSchema=z.object({recommendation_run_id:z.string(),recommendation:z.string(),confidence:z.number(),summary:z.string(),recommendation_sha256:z.string(),evidence_refs:z.array(z.unknown()),policy_refs:z.array(z.unknown()),contradiction_refs:z.array(z.unknown()),changed_fact_refs:z.array(z.unknown()),missing_evidence:z.array(z.unknown()),requires_human_review:z.boolean(),adjudication_authority:z.string(),created_at:z.union([z.string(),z.date()])});
const providerCheckpointSchema=z.object({checkpoint_id:z.string(),thread_id:z.string(),checkpoint_version:z.number(),stage:z.string(),status:z.string(),state_sha256:z.string(),requires_human_action:z.boolean(),resumed_by_user_id:z.string().nullable(),resumed_at:z.union([z.string(),z.date()]).nullable()});
const providerMissingRequestSchema=z.object({request_id:z.string(),document_types:z.array(z.string()),rationale:z.string(),status:z.string(),requested_by_user_id:z.string(),created_at:z.union([z.string(),z.date()]),satisfied_at:z.union([z.string(),z.date()]).nullable()});
export const providerDisputeIntelligenceQueueSchema=z.array(providerDisputeQueueItemSchema);
export const providerDisputeIntelligenceWorkbenchSchema=z.object({recovery_case_id:z.string(),dispute:recoveryDisputeSchema,snapshot:providerSnapshotSchema.nullable(),reingestions:z.array(providerReingestionSchema),comparisons:z.array(providerComparisonSchema),latest_rag:z.object({run_id:z.string(),snapshot_id:z.string(),strategy:z.string(),selected_count:z.number(),citation_coverage:z.number(),contradiction_count:z.number(),changed_fact_count:z.number(),pack_sha256:z.string(),items:z.array(evidenceSearchItemSchema)}).nullable(),recommendations:z.array(providerRecommendationSchema),checkpoints:z.array(providerCheckpointSchema),missing_evidence_requests:z.array(providerMissingRequestSchema),provider_responses:z.array(z.record(z.string(),z.unknown())),human_authority:z.record(z.string(),z.unknown())});
export type ProviderDisputeIntelligenceQueue=z.infer<typeof providerDisputeIntelligenceQueueSchema>;
export type ProviderDisputeQueueItem=z.infer<typeof providerDisputeQueueItemSchema>;
export type ProviderDisputeIntelligenceWorkbench=z.infer<typeof providerDisputeIntelligenceWorkbenchSchema>;
export type EvidenceSearchResult=z.infer<typeof evidenceSearchResultSchema>;

const providerResolutionPacketSchema=z.object({packet_id:z.string(),dispute_id:z.string(),snapshot_id:z.string(),snapshot_sha256:z.string(),recommendation_run_id:z.string().nullable(),outcome:z.string(),original_target_amount:z.string(),amended_target_amount:z.string(),financial_delta:z.string(),material_target_change:z.boolean(),recommendation_disagreement:z.boolean(),completeness:z.unknown(),blocker_codes:z.array(z.string()),dual_control_required:z.boolean(),status:z.string(),packet_version:z.number(),expected_case_version:z.number(),locked_payload_sha256:z.string().nullable(),primary_resolver_user_id:z.string(),second_resolver_user_id:z.string().nullable(),final_resolution_id:z.string().nullable()});
const providerFinalResolutionSchema=z.object({resolution_id:z.string(),outcome:z.string(),original_target_amount:z.string(),amended_target_amount:z.string(),financial_delta:z.string(),snapshot_sha256:z.string(),packet_locked_sha256:z.string(),position_version_id:z.string(),correspondence_id:z.string().nullable(),reversal_referral_id:z.string().nullable(),payload_sha256:z.string(),resolved_at:z.union([z.string(),z.date()])});
const reversalReferralSchema=z.object({reversal_referral_id:z.string(),referral_type:z.string(),destination:z.string(),amount:z.string(),currency:z.string(),status:z.string(),external_reference:z.string().nullable(),verified_by_user_id:z.string().nullable(),verified_at:z.union([z.string(),z.date()]).nullable(),payload_sha256:z.string()});
export const providerDisputeResolutionSchema=z.object({recovery_case_id:z.string(),dispute_id:z.string(),dispute_status:z.string(),recovery_case_version:z.number(),current_target_recovery_amount:z.string(),packet:providerResolutionPacketSchema.nullable(),final_resolution:providerFinalResolutionSchema.nullable(),position_versions:z.array(z.record(z.string(),z.unknown())),reversal_referrals:z.array(reversalReferralSchema),audit_chain:z.array(z.record(z.string(),z.unknown())),authority:z.record(z.string(),z.unknown())});
export type ProviderDisputeResolution=z.infer<typeof providerDisputeResolutionSchema>;
export type ReversalReferral=z.infer<typeof reversalReferralSchema>;

const settlementCaseSchema=z.object({settlement_case_id:z.string(),recovery_case_id:z.string(),claim_id:z.string(),provider_organization_id:z.string(),final_resolution_id:z.string(),position_version_id:z.string(),position_payload_sha256:z.string(),target_amount:z.string(),verified_amount:z.string(),remaining_amount:z.string(),currency:z.string(),status:z.string(),case_version:z.number(),created_at:z.union([z.string(),z.date()]),updated_at:z.union([z.string(),z.date()]),certified_at:z.union([z.string(),z.date()]).nullable()});
const settlementEvidenceSchema=z.object({settlement_evidence_id:z.string(),evidence_type:z.string(),amount:z.string(),currency:z.string(),installment_sequence:z.number(),external_reference:z.string(),bank_reference:z.string().nullable(),remittance_reference:z.string().nullable(),provider_reference:z.string().nullable(),evidence_refs:z.array(z.unknown()),evidence_payload_sha256:z.string(),status:z.string(),reference_match:z.boolean().nullable().optional(),verification_rationale:z.string().nullable(),submitted_by_user_id:z.string(),verified_by_user_id:z.string().nullable(),occurred_at:z.union([z.string(),z.date()]),verified_at:z.union([z.string(),z.date()]).nullable()});
const ledgerCorrelationSchema=z.object({correlation_id:z.string(),settlement_evidence_id:z.string(),journal_id:z.string(),period_id:z.string(),amount:z.string(),currency:z.string(),status:z.string(),correlation_payload_sha256:z.string()});
const settlementExceptionSchema=z.object({exception_id:z.string(),exception_code:z.string(),severity:z.string(),details:z.unknown(),status:z.string(),created_at:z.union([z.string(),z.date()])});
const completionCertificateSchema=z.object({certificate_id:z.string(),accounting_period_id:z.string(),prepared_by_user_id:z.string(),approved_by_user_id:z.string().nullable(),target_amount:z.string(),verified_amount:z.string(),remaining_amount:z.string(),status:z.string(),payload_sha256:z.string(),prepared_at:z.union([z.string(),z.date()]),certified_at:z.union([z.string(),z.date()]).nullable()});
export const recoverySettlementQueueSchema=z.array(settlementCaseSchema);
export const recoverySettlementPortfolioSchema=z.object({cases:z.number(),open_cases:z.number(),target_recovery:z.string(),verified_recovery:z.string(),remaining_balance:z.string()}).passthrough();
export const recoverySettlementWorkbenchSchema=z.object({case:settlementCaseSchema,evidence:z.array(settlementEvidenceSchema),ledger_correlations:z.array(ledgerCorrelationSchema),exceptions:z.array(settlementExceptionSchema),certificate:completionCertificateSchema.nullable(),correspondence:z.array(z.record(z.string(),z.unknown())),tasks:z.array(operationsTaskSchema),aging:z.object({age_days:z.number(),bucket:z.string()}),audit_chain:z.array(auditEventSchema),authority:z.record(z.string(),z.unknown())});
export type RecoverySettlementQueue=z.infer<typeof recoverySettlementQueueSchema>;
export type RecoverySettlementCase=z.infer<typeof settlementCaseSchema>;
export type RecoverySettlementPortfolio=z.infer<typeof recoverySettlementPortfolioSchema>;
export type RecoverySettlementWorkbench=z.infer<typeof recoverySettlementWorkbenchSchema>;

const settlementCitationSchema=z.object({citation_id:z.string(),type:z.string(),retrieval_score:z.number().optional()}).passthrough();
const settlementCaseMetricSchema=z.object({settlement_case_id:z.string(),claim_id:z.string(),provider_organization_id:z.string(),currency:z.string(),target_recovery:z.string(),verified_recovery:z.string(),remaining_balance:z.string(),under_recovery_amount:z.string(),over_recovery_amount:z.string(),repayment_amount:z.string(),offset_amount:z.string(),age_days:z.number(),aging_bucket:z.string(),status:z.string(),certified:z.boolean(),effectiveness_score:z.number(),anomalies:z.array(z.object({code:z.string(),severity:z.string()}).passthrough()),citations:z.array(settlementCitationSchema)});
export const providerBalanceStatementSchema=z.object({authority:z.record(z.string(),z.unknown()),provider_organization_id:z.string(),as_of_date:z.string(),currency:z.string(),target_recovery:z.string(),verified_recovery:z.string(),remaining_balance:z.string(),under_recovery_amount:z.string(),over_recovery_amount:z.string(),open_case_count:z.number(),certified_case_count:z.number(),aging_summary:z.record(z.string(),z.number()),case_lines:z.array(settlementCaseMetricSchema),source_watermark_sha256:z.string(),statement_id:z.string().optional(),statement_version:z.number().optional(),payload_sha256:z.string().optional(),created_at:z.union([z.string(),z.date()]).optional(),delivered:z.boolean().optional(),history:z.array(z.record(z.string(),z.unknown())).optional()});
const settlementPortfolioKpisSchema=z.object({settlement_cases:z.number(),certified_cases:z.number(),open_cases:z.number(),target_recovery:z.string(),verified_recovery:z.string(),remaining_balance:z.string(),under_recovery_amount:z.string(),over_recovery_amount:z.string(),recovery_effectiveness_pct:z.number(),open_exception_count:z.number(),provider_count:z.number(),currency_totals:z.record(z.string(),z.unknown())});
const settlementSignalSchema=z.object({code:z.string(),severity:z.string(),settlement_case_id:z.string(),provider_organization_id:z.string()}).passthrough();
export const recoverySettlementIntelligencePortfolioSchema=z.object({authority:z.record(z.string(),z.unknown()),kpis:settlementPortfolioKpisSchema,aging:z.record(z.string(),z.number()),providers:z.array(providerBalanceStatementSchema),cases:z.array(settlementCaseMetricSchema),settlement_exceptions:z.array(settlementSignalSchema),source_watermark_sha256:z.string()});
export const recoverySettlementCloseoutReportSchema=z.object({report_type:z.string(),period_id:z.string(),period_key:z.string(),period_status:z.string(),period_close_sha256:z.string().nullable(),certificate_count:z.number(),certificates:z.array(z.record(z.string(),z.unknown())),total_verified:z.string(),authority:z.string(),source_watermark_sha256:z.string(),report_id:z.string().nullable(),report_version:z.number().nullable(),manifest_sha256:z.string()});
export const recoverySettlementExceptionInvestigationSchema=z.object({investigation_id:z.string(),settlement_case_id:z.string(),exception_code:z.string(),severity:z.string(),explanation:z.string(),factors:z.array(z.unknown()),citations:z.array(settlementCitationSchema),recommendations:z.array(z.string()),authority:z.record(z.string(),z.unknown()),payload_sha256:z.string()});
export const recoverySettlementTraceSchema=z.object({settlement_case_id:z.string(),claim_id:z.string(),lineage:z.record(z.string(),z.unknown()),authority:z.record(z.string(),z.unknown())});
export const recoverySettlementCopilotSchema=z.object({run_id:z.string(),answer:z.string(),citations:z.array(settlementCitationSchema),retrieval_strategy:z.string(),source_watermark_sha256:z.string(),authority:z.record(z.string(),z.unknown()),payload_sha256:z.string()});
export type RecoverySettlementIntelligencePortfolio=z.infer<typeof recoverySettlementIntelligencePortfolioSchema>;
export type ProviderRecoveryBalanceStatement=z.infer<typeof providerBalanceStatementSchema>;
export type RecoverySettlementCloseoutReport=z.infer<typeof recoverySettlementCloseoutReportSchema>;
export type RecoverySettlementExceptionInvestigation=z.infer<typeof recoverySettlementExceptionInvestigationSchema>;
export type RecoverySettlementTrace=z.infer<typeof recoverySettlementTraceSchema>;
export type RecoverySettlementCopilot=z.infer<typeof recoverySettlementCopilotSchema>;

const controlResultSchema=z.object({control_code:z.string(),passed:z.boolean(),details:z.unknown()}).passthrough();
const controlPackageSchema=z.object({package_id:z.string(),package_version:z.number(),status:z.string(),correction_of_package_id:z.string().nullable(),amendment_reason:z.string().nullable(),manifest:z.unknown(),validation_results:z.unknown(),material_blockers:z.array(z.unknown()),source_watermark_sha256:z.string(),manifest_sha256:z.string(),locked_manifest_sha256:z.string().nullable(),maker_user_id:z.string(),checker_user_id:z.string().nullable(),created_at:z.union([z.string(),z.date()]),locked_at:z.union([z.string(),z.date()]).nullable(),certified_at:z.union([z.string(),z.date()]).nullable(),staged_at:z.union([z.string(),z.date()]).nullable(),submitted_at:z.union([z.string(),z.date()]).nullable()});
const controlAttestationSchema=z.object({attestation_id:z.string(),attestation_version:z.number(),control_results:z.array(controlResultSchema),material_blockers:z.array(z.unknown()),control_effectiveness_pct:z.number(),source_watermark_sha256:z.string(),payload_sha256:z.string(),created_by_actor_type:z.string(),created_at:z.union([z.string(),z.date()])});
const controlQueueItemSchema=z.object({reporting_period_id:z.string(),period_key:z.string(),status:z.string(),latest_package_status:z.string(),material_blockers:z.array(z.unknown()),control_effectiveness_pct:z.number().nullable()});
export const recoveryControlAssuranceDashboardSchema=z.object({authority:z.record(z.string(),z.unknown()),kpis:z.object({reporting_periods:z.number(),packages:z.number(),certified_packages:z.number(),submitted_packages:z.number(),average_control_effectiveness_pct:z.number(),material_blocked_periods:z.number()}),operational_queue:z.array(controlQueueItemSchema)});
export const recoveryControlAssuranceWorkbenchSchema=z.object({authority:z.record(z.string(),z.unknown()),period:z.object({reporting_period_id:z.string(),period_key:z.string(),report_type:z.string(),jurisdiction:z.string(),start_date:z.union([z.string(),z.date()]),end_date:z.union([z.string(),z.date()]),accounting_period_ids:z.array(z.string()),status:z.string()}),latest_attestation:controlAttestationSchema.nullable(),packages:z.array(controlPackageSchema),certification_chain:z.array(z.object({certification_id:z.string(),package_id:z.string(),sequence:z.number(),maker_user_id:z.string(),checker_user_id:z.string(),previous_certification_sha256:z.string().nullable(),certification_sha256:z.string(),certified_at:z.union([z.string(),z.date()])})),audit_chain:z.array(auditEventSchema)});
export const recoveryControlAssuranceTraceSchema=z.object({package:controlPackageSchema,control_evidence_samples:z.array(z.record(z.string(),z.unknown())),certification:z.record(z.string(),z.unknown()).nullable(),submission_receipt:z.record(z.string(),z.unknown()).nullable(),annotations:z.array(z.record(z.string(),z.unknown())),provenance:z.string(),authority:z.record(z.string(),z.unknown())});
export type RecoveryControlAssuranceDashboard=z.infer<typeof recoveryControlAssuranceDashboardSchema>;
export type RecoveryControlAssuranceWorkbench=z.infer<typeof recoveryControlAssuranceWorkbenchSchema>;
export type RecoveryControlPackage=z.infer<typeof controlPackageSchema>;
export type RecoveryControlAssuranceTrace=z.infer<typeof recoveryControlAssuranceTraceSchema>;


export const mutationResponseSchema=z.record(z.string(),z.unknown());
export type MutationResponse=z.infer<typeof mutationResponseSchema>;

export const leaseAcquisitionSchema=z.object({lease_token:z.string(),lease_version:z.number(),expires_at:z.union([z.string(),z.date()]),case:z.unknown().optional()}).passthrough();
export type LeaseAcquisition=z.infer<typeof leaseAcquisitionSchema>;

export const financialCopilotSchema=z.object({run_id:z.string(),answer:z.string(),citations:z.array(financialCitationSchema),retrieval_strategy:z.string(),source_watermark_sha256:z.string(),authority:z.record(z.string(),z.unknown()),payload_sha256:z.string()});
export type FinancialCopilot=z.infer<typeof financialCopilotSchema>;

export const financialAnomalyInvestigationSchema=z.object({investigation_id:z.string(),claim_id:z.string(),anomaly_code:z.string(),anomaly_score:z.number(),severity:z.string(),explanation:z.string(),factors:z.array(z.unknown()),citations:z.array(financialCitationSchema),recommendations:z.array(z.string()),authority:z.record(z.string(),z.unknown()),payload_sha256:z.string()});
export type FinancialAnomalyInvestigation=z.infer<typeof financialAnomalyInvestigationSchema>;
