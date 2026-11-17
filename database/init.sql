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

CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) NOT NULL UNIQUE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS organization_members (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(50) NOT NULL DEFAULT 'MEMBER',
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
  id VARCHAR(255) PRIMARY KEY,
  repository_id UUID REFERENCES repositories(id) ON DELETE SET NULL,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(255),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversation_messages (
  id UUID PRIMARY KEY,
  conversation_id VARCHAR(255) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role VARCHAR(50) NOT NULL,
  content TEXT NOT NULL,
  citations TEXT,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reports (
  id UUID PRIMARY KEY,
  repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
  owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  report_type VARCHAR(50) NOT NULL DEFAULT 'assessment',
  format VARCHAR(20) NOT NULL DEFAULT 'pdf',
  analysis_id UUID REFERENCES analyses(id) ON DELETE SET NULL,
  maintainability_score INTEGER NOT NULL DEFAULT 0,
  technical_debt_hours INTEGER NOT NULL DEFAULT 0,
  findings_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS indexing_metadata (
  id UUID PRIMARY KEY,
  repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
  commit_sha VARCHAR(64) NOT NULL,
  chunks_count INTEGER NOT NULL DEFAULT 0,
  indexed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_repo_commit_index UNIQUE (repository_id, commit_sha)
);
