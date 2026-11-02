# Payment Reconciler — recording script

Indicaciones para ti en español; narración en inglés. No leas las líneas que empiezan por ↳.

Los intervalos suman 5:00, pero debes ensayar con cronómetro para incluir cambios de pantalla y pausas. El texto no garantiza por sí solo una duración exacta.

## Antes de grabar — no leer

- Inicia la aplicación en http://127.0.0.1:5050 y abre el panel sin filtros.
- Datos comprobados: PAY-001 matched; PAY-002 discrepancy de monto; PAY-003 unmatched; PAY-004 discrepancy de moneda; PAY-005 requires_review. INV-001 Paid; INV-002, INV-003 e INV-004 Pending.
- Las tarjetas dicen “Pending invoices” y “Paid invoices”, con cantidades 3 y 1.
- Abre de antemano las páginas de detalle de PAY-002, PAY-004 y PAY-001 en pestañas separadas. En la base actual sus URL son /payments/2, /payments/4 y /payments/1; usa “View details” si los identificadores cambian.
- Abre las pestañas de código indicadas, incluida migrations/001_initial.sql. Busca los métodos con la búsqueda del editor para no depender de números de línea.
- Mantén cámara y pantalla visibles. Prepara otra terminal en Challenge con .venv activado.
- No busques Pending en el detalle de un pago: se encuentra en el panel principal, tabla Invoices, columna Status.
- No es necesario modificar código ni restablecer datos para esta grabación. Reenviar PAY-001 no cambia las cantidades.

## Recording timeline

## 0:00–0:25 · Presentación

↳ ABRE panel → “Every payment, explained.”
Hi, I'm Santiago. For this challenge, I built a payment reconciler.
↳ SEÑALA tarjetas → “Pending invoices”: 3 / “Paid invoices”: 1
I chose an operations problem: comparing expected invoices with the payments reported by a provider.
Those reports can contain discrepancies or repeated events.
My goal was to identify these situations and clearly explain each outcome in a small application that's easy to run locally.

## 0:25–0:55 · Pago correcto y diferencia de monto

↳ MUESTRA tabla de pagos
These examples use synthetic data.
↳ SEÑALA PAY-001 → Matched
PAY-001 matches its invoice, so the payment is matched and the invoice becomes paid.
↳ ABRE PAY-002 → View details
PAY-002 received eighty thousand Colombian pesos, but the invoice expected ninety thousand.
↳ EN EL DETALLE de PAY-002, SEÑALA las tarjetas “Received amount” (COP 80,000.00) → “Current expected amount” (COP 90,000.00) → texto “The payment amount does not match the invoice.”
Here, I can compare both amounts and read the explanation.
↳ PULSA “Back to operations”. BAJA hasta la tabla “Invoices”. SEÑALA la fila INV-002 y la columna “Status”: “Pending”. No aparece en el detalle del pago.
The invoice remains pending because the application does not treat this difference as a full payment.

## 0:55–1:25 · Los demás escenarios

↳ En el panel, SUBE hasta “Received payments” y SEÑALA PAY-003, su referencia UNKNOWN y resultado “Unmatched”.
PAY-003 has an unknown invoice reference.
↳ ABRE “View details” de PAY-004. SEÑALA “Received amount”: USD 50,000.00 y “Current expected amount”: COP 50,000.00.
For PAY-004, the numeric amounts are equal, but the currencies are different. The application does not convert currencies.
↳ PULSA “Back to operations”. SEÑALA PAY-005, referencia INV-001 y etiqueta “Requires review”.
PAY-005 is a different event for an invoice that's already paid, so it requires review.
↳ BAJA a “Invoices”, fila INV-004: COP 75,000.00 y estado “Pending”. Esta factura no aparece entre las referencias de los pagos.
Finally, INV-004 remains pending because it has no payments.
The dashboard helps operations identify each of these situations separately.

## 1:25–1:50 · Dónde empieza la aplicación

↳ ABRE app/__init__.py → create_app()
The application starts in create_app.
↳ SEÑALA Flask → Database → Repository → Service → Blueprints
Here, I configure Flask and connect the database, repository, and service. I register the routes using Blueprints.
↳ ABRE app/entry_point/api.py → receive_payment(), debajo de @api.post("/api/payment-events"). No es el método del servicio aunque comparten nombre.
When a payment arrives, the API passes its JSON data to the service and returns the outcome.
↳ SEÑALA HTTP 201 y 200
The API returns HTTP two hundred and one for a new event, and HTTP two hundred for an existing event.

## 1:50–2:15 · Servicio y validación

↳ ABRE app/application/services.py → ReconciliationService.receive_payment(self, data). SEÑALA payment = parse_input(data, PaymentInput) y return self.repository.receive_payment(payment, reconcile). Aquí no se muestra ningún estado Pending.
The service coordinates input validation and persistence.
↳ ABRE app/domain/models.py → parse_input(data, model). SEÑALA la comparación de campos y la validación del monto y moneda.
Validation checks required fields, positive amounts, and supported currencies.
↳ SEÑALA amount_minor
I represent money as integer minor units, such as cents, to avoid floating-point arithmetic.
↳ SEÑALA normalización de espacios y monedas
I also normalize whitespace and currency codes.
This gives the business rules and repository a consistent input format before processing.

## 2:15–2:45 · Protección contra duplicados

↳ ABRE app/infrastructure/repositories.py → SQLiteRepository.receive_payment(self, payment, decide). SEÑALA with self.database.transaction() as connection y el SELECT WHERE provider=? AND event_id=?. El método transaction se define en database.py; aquí solo se utiliza.
In the repository, I open a transaction and look up the provider and event identifier.
↳ SEÑALA return dict(existing), False
If the event already exists with the same data, I return the stored record without repeating its effects.
↳ SEÑALA comparación → conflicto
If the same identifier arrives with different content, I return a conflict.
↳ ABRE migrations/001_initial.sql, tabla payment_events. SEÑALA exactamente UNIQUE(provider,event_id). El índice one_match_per_invoice es otra protección, para una factura con un único pago conciliado; no los confundas.
A unique database constraint also protects against duplicates, even when two requests arrive at the same time.

## 2:45–3:10 · Reglas de negocio

↳ ABRE domain/reconciliation.py → reconcile()
The business decision lives in this function.
↳ RECORRE inexistente → pagada → moneda → monto
I check whether the invoice exists, whether it was already paid, and whether the currency and amount match.
↳ SEÑALA return Decision(...). Si necesitas los nombres de los campos, están arriba en la clase Decision: result y reason. “Outcome” es la etiqueta de la página, no el nombre del atributo en Python.
Each branch returns an outcome and a reason.
↳ MUESTRA función sin SQL ni Flask
This function does not depend on Flask or execute SQL.
That lets me test the business scenarios independently from the web framework and the database.

## 3:10–3:35 · Transacciones y consistencia

↳ VUELVE al repositorio → factura + pago + auditoría
I save the invoice update, payment outcome, and audit history within the same transaction.
↳ ABRE infrastructure/database.py → commit() y rollback()
If all writes succeed, I commit the changes. If any write fails, I roll back the operation.
↳ QUÉDATE en database.py y SEÑALA el bloque try/except de transaction(). Las escrituras SQL se mostraron antes en repositories.py; no las busques en este archivo.
This prevents an invoice from being marked as paid while its payment information is incomplete.
↳ SEÑALA rollback()
After a failed request, the client can safely resend the event.

## 3:35–3:55 · Panel e historial

↳ ABRE entry_point/web.py → dashboard() / render_template()
The dashboard queries the repository and passes the records to an HTML template.
↳ CAMBIA al navegador, detalle de PAY-001. BAJA hasta “Audit history” y SEÑALA los títulos “Payment received” y “Reconciliation completed”. Los códigos received y completed se traducen a estas etiquetas en la interfaz.
Operations can review the explanation and audit entries for each payment.
↳ MUESTRA el panel
I chose Flask and SQLite to make local execution straightforward.
Because reconciliation is short and makes no external network calls, it runs within the request, without a background process.

## 3:55–4:25 · Demostración del duplicado

↳ EJECUTA el curl en la segunda terminal
```sh
curl -i http://127.0.0.1:5050/api/payment-events \
  -H 'Content-Type: application/json' \
  -d '{"provider":"demo","event_id":"PAY-001","invoice_reference":"INV-001","amount_minor":15000000,"currency":"COP"}'
```
Now, I resend PAY-001 with exactly the same data.
↳ SEÑALA HTTP 200 y created: false
The response is HTTP two hundred, and created is false. The API returns the existing payment.
↳ VUELVE al panel principal, filtro “All”, y pulsa “Refresh”. SEÑALA las cinco filas de “Received payments” y un único PAY-001. No hay una tarjeta con el contador de eventos; estás mostrando las filas.
After refreshing the dashboard, there are still five events and only one PAY-001.
↳ SEÑALA PAY-005 → otro identificador
This differs from PAY-005, which has a different event identifier.
↳ SEÑALA otra vez la fila PAY-001 en el panel; no hace falta abrir su detalle.
Idempotency prevents repeated reports from creating duplicate effects. Distinct events still need their own business evaluation.

## 4:25–4:40 · Pruebas automatizadas

↳ EJECUTA python -m pytest -q
The automated tests cover business rules, input validation, concurrent duplicate requests, and transaction rollback.
↳ SEÑALA el resultado final real
They also verify that the demo covers every outcome and that resetting the examples backs up the previous records.

## 4:40–5:00 · Uso de IA y cierre

↳ MUESTRA panel o README
I used AI to support the design, implementation, tests, and documentation.
I simplified the initial proposal to keep the scope focused.
This demo does not move real money or support partial payments.
↳ MIRA a cámara
Next, I would validate the rules with operations and add authentication and discrepancy resolution.
↳ MIRA a cámara para terminar
Thank you for reviewing my project.
FIN · Termina la grabación al llegar a 5:00.



## Referencia rápida — no leer

| Qué buscas | Dónde está realmente |
|---|---|
| Pending de INV-002 | Navegador, panel principal, Invoices → INV-002 → Status |
| Discrepancy de PAY-002 | Received payments → Outcome, o título de su detalle |
| Motivo del resultado | Columna Reason, o debajo del título Discrepancy en el detalle |
| Validación del pago | services.py → receive_payment llama a models.py → parse_input |
| Protección contra evento repetido | repositories.py → receive_payment → existing |
| Restricción de evento único | migrations/001_initial.sql → UNIQUE(provider,event_id) |
| commit y rollback | database.py → Database.transaction |
| Historial visible | Detalle de PAY-001 → Audit history |
| Resultado estable para API | Campo result: matched, discrepancy, unmatched, requires_review |

La factura puede quedar Pending aunque el pago tenga un resultado definitivo como Discrepancy. No existe un pago esperando a un worker en esta versión: la conciliación es inmediata.
