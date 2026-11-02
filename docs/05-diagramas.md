# Project diagrams

Reconciliation happens within the same HTTP request. Invoices are registered beforehand.

## Flowchart

```mermaid
flowchart TD
    A[Receive payment] --> B{Valid input?}
    B -- No --> C[Return 400]
    B -- Yes --> D[Open transaction and look up event]
    D --> E{Already exists?}
    E -- Yes --> F{Same data?}
    F -- Yes --> G[Return existing record: 200]
    F -- No --> H[Return conflict: 409]
    E -- No --> I[Find invoice]
    I --> J{Invoice exists?}
    J -- No --> K[Unmatched]
    J -- Yes --> L{Already paid?}
    L -- Yes --> M[Requires review]
    L -- No --> N{Amount and currency match?}
    N -- No --> O[Discrepancy]
    N -- Yes --> P[Matched: mark invoice paid]
    K --> Q[Save payment and audit history]
    M --> Q
    O --> Q
    P --> Q
    Q --> R[Commit transaction and return 201]
    Q -. On failure .-> S[Roll back and return error]
    R --> T[Review outcome on dashboard]
```

## Sequence diagram

```mermaid
sequenceDiagram
    actor U as Client
    participant A as Flask API
    participant S as Service
    participant R as Repository
    participant DB as SQLite
    participant D as Business rule
    U->>A: Submit payment
    A->>S: Validate and register
    S->>R: Normalized payment and rule
    R->>DB: Open transaction and find event
    alt Existing event
        DB-->>R: Existing data
        R-->>S: Existing record or conflict
        S-->>A: Existing record or conflict
        A-->>U: 200 or 409
    else New event
        R->>DB: Insert event and find invoice
        DB-->>R: Invoice or no match
        R->>D: Compare payment and invoice
        D-->>R: Outcome and reason
        R->>DB: Store outcome, audit and invoice update
        R->>DB: COMMIT
        R-->>S: Payment outcome
        S-->>A: Result
        A-->>U: 201
    end
    Note over R,DB: Failed writes roll back the entire transaction
```

A unique key prevents duplicate events. A transaction prevents partial writes. The dashboard reads the stored outcome and audit history.
