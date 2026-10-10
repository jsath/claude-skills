# Personal identity, password-manager, and 2FA review

Use when advising on authenticator apps, password managers, TOTP, passkeys, hardware security keys, recovery codes, phone loss, or account lockout.

## Core tradeoff

Storing a password and its TOTP seed in the same password-manager vault weakens strict factor separation: compromise of an unlocked vault may expose both. It often improves real-world reliability and 2FA adoption because codes sync across trusted devices and phone loss no longer destroys the only authenticator.

Do not describe password-manager TOTP as categorically "more secure." Describe it as generally more reliable and convenient, with a concentration-of-risk tradeoff.

## Recommended tiers

### Ordinary accounts

- Unique generated password in the password manager.
- TOTP in the password manager is an acceptable default.
- Avoid SMS except as a constrained fallback when stronger methods are unavailable.

### Critical accounts

Prefer passkeys or phishing-resistant hardware security keys for:

- the password manager itself;
- primary email;
- Apple/Google identity;
- financial accounts where supported;
- cloud, source-control and domain infrastructure;
- crypto exchanges and custody accounts.

Keep at least two registered hardware keys: one carried and one stored securely.

## Bootstrap and recovery rule

Never keep the only way to recover the password manager inside that same vault.

Maintain outside the vault:

- printed/offline Emergency Kit or equivalent;
- account Secret Key where applicable;
- strong memorized account password;
- recovery codes;
- a separate authenticator or hardware key for the password manager's own MFA;
- at least one additional trusted logged-in device;
- a tested process to revoke a lost device.

The primary email account also needs an independent recovery path because it is often the recovery root for every other account.

## Review checklist

1. Inventory critical accounts and current MFA method.
2. Replace password reuse and SMS where possible.
3. Register two hardware keys/passkeys on critical accounts.
4. Move ordinary TOTP seeds to the password manager if reliability is the priority.
5. Keep the password manager's own recovery and MFA bootstrap separate.
6. Store recovery codes offline and test one non-destructive recovery path.
7. Add a second trusted device and confirm lost-device revocation.
8. Never publish screenshots containing QR codes, TOTP seeds, recovery codes, Secret Keys, account IDs, addresses or payment authorization data.

## Communication rule

Lead with the practical answer, then state the factor-separation caveat. Avoid fearmongering. The goal is a recoverable, phishing-resistant system the user will actually maintain.
