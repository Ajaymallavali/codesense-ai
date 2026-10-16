CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  display_name VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  github_username VARCHAR(255),
  github_token VARCHAR(255),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repositories (
  id UUID PRIMARY KEY,
  owner_id UUID NOT NULL REFERENCES users(id),
  github_id BIGINT,
  name VARCHAR(255) NOT NULL,
  full_name VARCHAR(500) NOT NULL,
  default_branch VARCHAR(255) NOT NULL DEFAULT 'main',
  language VARCHAR(100),
  imported_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analyses (
  id UUID PRIMARY KEY,
  repository_id UUID NOT NULL REFERENCES repositories(id),
  branch VARCHAR(255) NOT NULL,
  commit_sha VARCHAR(64),
  maintainability_score INTEGER DEFAULT 0,
  technical_debt_hours INTEGER DEFAULT 0,
  status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
  progress INTEGER DEFAULT 0,
  error_message TEXT,
  started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS findings (
  id UUID PRIMARY KEY,
  analysis_id UUID NOT NULL REFERENCES analyses(id),
  category VARCHAR(100) NOT NULL,
  severity VARCHAR(50) NOT NULL,
  file_path TEXT NOT NULL,
  title TEXT NOT NULL,
  suggestion TEXT,
  line_number INTEGER
);
