CREATE TABLE IF NOT EXISTS valid_citations AS
SELECT
    c.app_id,
    c.parsed AS patent_id
FROM citations c
WHERE EXISTS (
    SELECT 1
    FROM applications a
    WHERE a.app_id = c.app_id
)
AND EXISTS (
    SELECT 1
    FROM claims cl
    WHERE cl.patent_id = c.parsed
);

CREATE INDEX IF NOT EXISTS idx_valid_citations_app_id
ON valid_citations(app_id);

CREATE INDEX IF NOT EXISTS idx_valid_citations_patent_id
ON valid_citations(patent_id);