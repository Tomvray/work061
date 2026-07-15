
CREATE TABLE IF NOT EXISTS claims (
    patent_id VARCHAR(255),
    claim_sequence INTEGER,
    claim_text TEXT,
    dependent TEXT,
    claim_number INTEGER,
    exemplary BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_claims_patent_id ON claims(patent_id, claim_number);

CREATE TABLE IF NOT EXISTS office_actions (
    app_id VARCHAR(255),
    ifw_number VARCHAR(255),
    document_cd VARCHAR(255),
    mail_dt DATE,
    art_unit VARCHAR(255),
    uspc_class VARCHAR(255),
    uspc_subclass VARCHAR(255),
    header_missing BOOLEAN,
    fp_missing BOOLEAN,
    rejection_fp_mismatch BOOLEAN,
    closing_missing BOOLEAN,
    rejection_101 BOOLEAN,
    rejection_102 BOOLEAN,
    rejection_103 BOOLEAN,
    rejection_112 BOOLEAN,
    rejection_dp BOOLEAN,
    objection BOOLEAN,
    allowed_claims INTEGER,
    cite102_gt1 INTEGER,
    cite103_gt3 INTEGER,
    cite103_eq1 INTEGER,
    cite103_max INTEGER,
    signature_type VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_office_actions_app_id ON office_actions(app_id);

CREATE TABLE IF NOT EXISTS citations (
    app_id VARCHAR(255),
    citation_pat_pgpub_id TEXT,
    parsed VARCHAR(255),
    ifw_number VARCHAR(255),
    action_type VARCHAR(255),
    action_subtype VARCHAR(255),
    form892 BOOLEAN,
    form1449 BOOLEAN,
    citation_in_oa BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_citations_app_id ON citations(app_id);
CREATE INDEX IF NOT EXISTS idx_citations_citation_parsed ON citations(parsed);

CREATE TABLE IF NOT EXISTS applications (
    app_id VARCHAR(255) PRIMARY KEY,
    year VARCHAR(4)
)