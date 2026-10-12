# Secure LLM communication automations

Use this reference when reviewing or designing a workflow that reads email or business messages, sends content to an LLM, and republishes the result through SMS, mobile notifications, voice, or another lower-trust endpoint.

This is a durable review method with a dated product-capability note (September 2026). Reverify provider behavior and plan/model eligibility against current first-party documentation before implementation.

## Core architecture method

1. **Separate product surfaces before choosing controls.** Distinguish the governed human workspace (for example, an Enterprise chat/mobile product) from the production API or cloud-model runtime. Seats, SSO, chat retention, and audit features do not automatically apply to API calls, and API zero-retention terms do not automatically cover chat/mobile interfaces.
2. **Draw the complete data path.** Include source system, event transport, queue, content fetch, parser, model processor, post-model policy gate, destination provider, endpoint/device, logs, error tracking, and support tooling. Name the data processor and retention policy at every hop.
3. **Enforce least privilege at the source.** Prefer resource-scoped workload identity over user credentials. For Exchange Online, current guidance favors Application RBAC with a management scope over legacy Application Access Policies. Test both allowed and denied resources with real API calls after permission caches settle.
4. **Check additive authorization paths.** A resource-scoped grant can be defeated by a second tenant-wide grant. For Exchange Application RBAC, Microsoft documents that unscoped Entra application permissions and Exchange RBAC permissions are additive; remove an unscoped `Mail.Read` grant when relying on scoped `Application Mail.Read`.
5. **Use event notifications only as signals.** Keep content out of the public webhook where practical, enqueue and acknowledge quickly, then fetch content inside a private worker. Add lifecycle renewal, immutable identifiers, idempotency, dead-letter handling, and delta reconciliation so dropped or duplicated notifications do not become silent omissions or duplicate sends.
6. **Authenticate content origin separately from address matching.** Exact sender allowlists are routing rules, not proof of identity. For email, use the trusted mail perimeter's SPF/DKIM/DMARC/composite-authentication result or a perimeter-stamped private header. Define accepted patterns from known-good samples and reject ambiguous outcomes.
7. **Treat all message content as adversarial.** Convert active HTML to bounded plain text; do not fetch links, remote images, QR codes, or attachments in the first version. Strip repeated quotes/signatures and record truncation. Assume a trusted sender account can still be compromised.
8. **Make the LLM a pure transformation.** No browser, tools, memory, files, email-send, calendar, messaging, or other action capability. Use a versioned policy and strict structured output. The model never chooses recipient, sender, template, permission, or control bypass.
9. **Apply deterministic controls after the model.** Validate schema, lengths, URLs, numbers, secrets, prompt leakage, and data classification. Use a fixed destination and template. High-risk content should degrade to an opaque “review in the source system” alert or no send.
10. **Treat SMS and voice endpoints as disclosure surfaces.** SMS is not a command channel. Exclude secrets, codes, payment instructions, sensitive personal data, and privileged detail. Address SIM swap, lock-screen previews, speaker announcements, shoulder surfing, logged-in device theft, carrier account recovery, MDM, and remote revocation.
11. **Log metadata by default, not content.** Record content hashes/IDs, timestamps, auth verdicts, parser/policy/model/schema versions, provider request IDs, DLP verdicts, and delivery status. Exclude bodies, summaries, phone numbers, prompts, tokens, keys, and webhook secrets unless a separately approved retention requirement exists.
12. **Require human and operational controls.** Add global and per-source kill switches, two-person approval for scope/model/prompt/destination changes, shadow mode, a no-action rule, incident revocation steps, and periodic entitlement/retention review.

## Prompt-injection boundary

A system prompt, delimiter, classifier, or “trusted sender” label is not a security boundary. Defense in depth requires:

- canonicalize and minimize content before inference;
- no model tools or credentials;
- no active content retrieval;
- strict schema and bounded fields;
- deterministic post-validation/DLP;
- fixed server-side routing and publication;
- explicit “external/untrusted AI summary” labeling;
- source-system verification before acting;
- adversarial fixtures covering hidden HTML, quoted-thread attacks, Unicode/base64 tricks, fake system messages, malicious signatures, oversized bodies, tracking pixels, links, QR codes, and attachments.

## Mobile text and voice capability checks

Never infer that a voice-enabled assistant can read another app's data. Verify separately:

- voice conversation exists;
- the target app exposes read access, not merely compose/share access;
- access covers new events, current selection, or full history;
- the exact plan, OS, app version, region, language, and rollout are eligible;
- lock-screen behavior and user-presence requirements;
- central auditability and revocation.

Capability note (September 2026, reverify before relying on it):

- Apple documented Siri reading incoming texts and the last message from a named person, plus replying.
- Apple documented Apple Intelligence visually summarizing unread messages under a conversation, but the reviewed page did not establish that Siri could speak that generated summary.
- Anthropic documented Claude voice mode on iOS while separately stating that its iOS Messages/email integration created new content but did not read existing messages or email.
- Apple Shortcuts documented message triggers by sender or contained phrase. Treat event-trigger automation as distinct from general/history access.
- Apple App Intents expose an app's own actions and entities to system surfaces; do not treat them as permission to enumerate another app's private database.

If centrally audited LLM summaries are mandatory but the phone OS does not expose the required data, redesign the source channel: route future business messages into an approved backend or enterprise messaging platform and expose only that governed data through a managed app. Do not use jailbreaks, spyware, personal database scraping, or logged-in desktop-client automation as an architectural workaround.

## Provider-selection checklist

For each candidate model path (direct API, AWS, Azure/Microsoft, Google Cloud):

- identify the contractual data processor and subprocessors;
- confirm commercial no-training defaults;
- confirm zero-retention eligibility for the exact model and every feature used;
- identify safety, abuse, legal-hold, feedback, and stateful-feature exceptions;
- confirm region/data residency, encryption, private networking, IAM, audit logging, support access, and deletion behavior;
- keep human-workspace and API retention claims separate;
- pin the approved model ID and re-review any model change.

For SMS providers, verify restricted API credentials, fixed recipient/sender enforcement in application policy, account/subaccount isolation, SSO/MFA, spend and geography alerts, message-body/number redaction behavior, residual operational/compliance retention, signed status webhooks, and telecom registration.

## Pilot evidence gates

A secure pilot should prove, not merely document:

- positive access to the intended source and negative access to unrelated resources;
- exact sender plus authentication-gate behavior under spoof/lookalike/failure cases;
- duplicate suppression and recovery after webhook outage/renewal failure;
- bounded webhook response time and asynchronous processing;
- zero external actions, recipient changes, prompt leakage, or prohibited data across an adversarial corpus;
- fact precision/recall with verbatim traceability for dates, names, and amounts;
- provider organization/model/retention configuration from captured metadata;
- sensitive-data absence in logs, traces, alerts, and provider consoles;
- kill switch, credential revocation, remote-device revocation, and rollback exercises;
- exact-device voice/read behavior, including a negative test for any claimed cross-app access.

## First-party research anchors (reverify before use)

- Exchange Application RBAC: https://learn.microsoft.com/en-us/exchange/permissions-exo/application-rbac
- Graph Outlook notifications: https://learn.microsoft.com/en-us/graph/outlook-change-notifications-overview
- Graph webhook delivery: https://learn.microsoft.com/en-us/graph/change-notifications-delivery-webhooks
- Graph subscription lifetime: https://learn.microsoft.com/en-us/graph/api/resources/subscription?view=graph-rest-1.0
- Microsoft 365 email authentication: https://learn.microsoft.com/en-us/defender-office-365/email-authentication-about
- Anthropic API retention/ZDR: https://platform.claude.com/docs/en/manage-claude/api-and-data-retention
- Anthropic commercial training policy: https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training
- Anthropic Enterprise retention controls: https://privacy.claude.com/en/articles/10440198-configure-custom-data-retention-controls-for-enterprise-plans
- Anthropic structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- AWS Bedrock data protection: https://docs.aws.amazon.com/bedrock/latest/userguide/data-protection.html
- AWS Bedrock data retention: https://docs.aws.amazon.com/bedrock/latest/userguide/data-retention.html
- Apple Siri text behavior: https://support.apple.com/guide/iphone/call-text-and-email-with-siri-iph80059011d/ios
- Apple Intelligence in Messages: https://support.apple.com/guide/iphone/use-apple-intelligence-in-messages-iph64709c5c3/ios
- Apple Shortcuts communication triggers: https://support.apple.com/guide/shortcuts/communication-triggers-apdd711f9dff/ios
- Apple App Intents: https://developer.apple.com/documentation/appintents/
- Claude iOS app integrations: https://support.claude.com/en/articles/11869619-use-claude-with-ios-apps
- Claude voice mode: https://support.claude.com/en/articles/11101966-use-voice-mode
- Twilio restricted API keys: https://www.twilio.com/docs/iam/api-keys/restricted-api-keys
- Twilio message redaction: https://www.twilio.com/docs/messaging/guides/privacy-message-redaction
- Twilio webhook security: https://www.twilio.com/docs/usage/webhooks/webhooks-security
- OWASP prompt-injection prevention: https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
