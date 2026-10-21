# Privacy notes

This application stores information about minors. Use fictitious records during development. Before using real information, the practice must assess its RGPD responsibilities, document a lawful basis, configure access and backups, and define retention and deletion procedures.

The `consent_signed_at` field records the date a practice collected consent. It is not a consent workflow or a substitute for legal review.

Student routes require a JWT and filter records by the signed-in professional's owner ID. Use a private `SECRET_KEY`, HTTPS in deployment, protected database backups, and individual accounts.

When OpenAI is enabled, report drafting uses the student's first name, goal area and description, session dates, and goal ratings or comments. The report service does not include surname, guardian contact data, school, birth date, or private student notes in its request. Review and edit every draft before sharing it.

When an adapter is configured, the original material text is sent to its API. The adapter can contact ARASAAC for selected words when pictograms are enabled. See [api-contract.md](api-contract.md).
