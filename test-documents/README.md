# Synthetic document fixtures

These files contain fictional identities, references, and values. They are intended
only for testing the Private CFO local desktop document workflow.

- `dummy-salary-slip.pdf`: select **Salary slip**; should produce monthly income `INR 87600.00`.
- `dummy-insurance-policy.pdf`: select **Insurance policy**; should produce insurance coverage `INR 5000000.00`.
- `dummy-epf-statement.pdf`: select **EPF statement**; should produce EPF balance `INR 534500.00`.
- `dummy-form-16.pdf`: select **Form 16**; should produce annual gross income `INR 1140000.00`.
- `dummy-bank-statement.pdf`: select **Bank statement**; should produce August 2026 monthly income `INR 87600.00`, expenses excluding EMI `INR 36500.00`, EMI payments `INR 12000.00`, and bank account balance `INR 159100.00`.

The `.txt` sources are retained so every value in the generated PDFs remains easy to audit.
