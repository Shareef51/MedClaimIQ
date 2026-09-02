# MedClaimIQ Recruiter Website Walkthrough

Use synthetic or de-identified scenarios only.

## 1. Secure sign-in

Start at `/login`. Explain that production uses enterprise OIDC Authorization Code + PKCE through a BFF, while the synthetic persona selector exists only for a non-production portfolio environment. Select **Claims reviewer**.

## 2. Operations command center

Open the reviewer overview and show claim volume/risk, SLA aging, recovery progress, regulatory exposure, RAG quality and agent/retrieval latency. Explain that these are operational signals rather than automated claim decisions.

## 3. Claims investigation

Open the claims queue, search/filter the queue and enter a claim workbench. Show evidence, citations, multimodal review and governance. Open **Advanced Investigation** to demonstrate clinical/FHIR verification, evidence relationships and AI orchestration without making those implementation concepts the primary reviewer navigation.

## 4. Human-governed decision

Show reviewer locking, evidence requests, notes, AI recommendation context and the governed decision surface. Emphasize that the AI does not approve or deny a medical claim; the human reviewer makes the authoritative decision and disagreements are captured with rationale and evidence references.

## 5. Patient/provider separation

Sign out and enter the **Patient portal** persona. Show claim status, document requests, upload acknowledgements, released decision notices, appeals and the safe timeline. Point out that internal agent reasoning and reviewer-only evidence are not exposed.

Then enter the **Provider portal** persona and show provider dispute evidence requests, recovery settlement evidence and immutable balance statements. Explain that these interfaces collect evidence and responses; they do not initiate payments or collections.

## 6. Regulatory and financial governance

Use the Audit & compliance or Operations administrator persona. Demonstrate examination readiness, commitments, remediation and portfolio assurance. Open a governed action dialog to show that rationale/evidence is collected in a structured UI rather than browser prompts.

## 7. Production-readiness story

Close by explaining the release boundary: technical readiness, security certification, operational readiness and final go-live are separately governed. Local demo mode cannot bypass production identity controls, and production promotion remains human-authorized.
