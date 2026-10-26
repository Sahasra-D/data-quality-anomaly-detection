SELECT COUNT(*) AS missing_amount
FROM transactions
WHERE amount IS NULL;

SELECT transaction_id, COUNT(*) AS cnt
FROM transactions
GROUP BY transaction_id
HAVING COUNT(*) > 1;

WITH ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY transaction_id
               ORDER BY transaction_date
           ) AS rn
    FROM transactions
)
SELECT *
FROM ranked
WHERE rn > 1;

SELECT transaction_id,
       CASE
           WHEN amount <= 0 THEN 'Non-positive amount'
           WHEN DATE(transaction_date) > DATE('now') THEN 'Future date'
           WHEN email NOT LIKE '%_@_%.__%' THEN 'Bad email'
           ELSE 'No issue detected'
       END AS issue
FROM transactions
WHERE amount <= 0
   OR DATE(transaction_date) > DATE('now')
   OR email NOT LIKE '%_@_%.__%';

WITH transaction_gaps AS (
    SELECT customer_id,
           transaction_date,
           (
               JULIANDAY(transaction_date) -
               JULIANDAY(
                   LAG(transaction_date) OVER (
                       PARTITION BY customer_id
                       ORDER BY transaction_date
                   )
               )
           ) * 1440 AS minutes_gap
    FROM transactions
    WHERE customer_id IS NOT NULL
)
SELECT *
FROM transaction_gaps
WHERE minutes_gap IS NOT NULL;

CREATE VIEW IF NOT EXISTS dq_summary AS
SELECT 'Missing amount' AS check_name,
       COUNT(*) AS failures
FROM transactions
WHERE amount IS NULL

UNION ALL

SELECT 'Negative amount',
       COUNT(*)
FROM transactions
WHERE amount < 0;
