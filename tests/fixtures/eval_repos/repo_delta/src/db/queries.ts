import { Pool } from "pg";

const pool = new Pool({
  connectionString: process.env.DATABASE_URL || "postgresql://app:secret@localhost:5432/appdb",
});

export async function findUserByEmail(email: string) {
  // Safe parameterized query
  const res = await pool.query("SELECT id, email, full_name, role FROM users WHERE email = $1", [email]);
  return res.rows[0] || null;
}

export async function listActiveAccounts() {
  const queryText = `
    SELECT u.id, u.email, a.balance, a.currency, a.status
    FROM users u
    JOIN accounts a ON a.user_id = u.id
    WHERE a.status = 'ACTIVE'
    ORDER BY a.created_at DESC
    LIMIT 50;
  `;
  const res = await pool.query(queryText);
  return res.rows;
}
