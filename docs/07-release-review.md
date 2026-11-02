# Pre-submission review

## Corrections

- Packaged the SQL schema so normal installations include it, rather than relying on an external source directory.
- Corrected outdated project metadata describing background processing.
- Limited invoice conflict handling to actual unique-constraint violations; unrelated integrity errors are no longer mislabeled as duplicate references.
- Made the review outcome filter label consistent with the displayed result.
- Expanded Git exclusions for build artifacts, custom local database files, environment overrides and the original challenge instructions PDF.

## Verification

- 26 automated tests passed on Python 3.12 and Python 3.15.
- Dependency consistency checks passed in the existing environment; the clean environment was also checked.
- Built and installed a wheel in a clean Python 3.12 environment.
- Exercised the installed package outside the checkout using a fresh temporary database.
- Verified initialization, repeatable demo loading, dashboard, payment detail, CSS, health and duplicate handling.
- Added coverage for two concurrent distinct payments against one invoice and normalized retries with reordered JSON keys.
- Used a temporary Git repository to inspect the proposed file set without staging or initializing the actual project.
- No apparent credentials were found in the reviewed application and documentation. The previous company project was outside this review and must not be included.

## Delivery status

Ready to prepare a GitHub repository for this local challenge scope. GitHub publication, repository creation, commits and access permissions have not been performed. Use Challenge as the repository root.

The application has no authentication and uses synthetic data. Database initialization creates missing tables but does not upgrade existing schemas. UI checks used Flask's client; this review did not include a visual browser inspection or a real banking integration.

Rehearsal scripts may refer to the previous test count; use the count printed by the current test run when recording.
